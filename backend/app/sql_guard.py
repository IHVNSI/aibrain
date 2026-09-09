"""SQL safety guard — production guardrails for the text-to-SQL pipeline.

Enforces:
  * Least privilege at the statement level: ONLY a single read-only SELECT/WITH
    statement is allowed. Destructive / DDL / DML commands are blocked.
  * Automatic default LIMIT to prevent runaway result sets.
  * Basic prompt-injection / multi-statement sanitization.

This complements (does not replace) connecting the pipeline to a DB user that
has SELECT-only privileges — that remains the strongest guarantee.
"""
import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)

# Commands that must never run through the assistant.
_FORBIDDEN = (
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "REPLACE", "MERGE", "GRANT", "REVOKE", "ATTACH", "DETACH", "VACUUM",
    "REINDEX", "PRAGMA", "EXEC", "EXECUTE", "CALL", "COPY", "INTO OUTFILE",
    "LOAD DATA",
)

DEFAULT_LIMIT = 100


def _strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"--[^\n]*", " ", sql)          # line comments
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)  # block comments
    return sql


def sanitize(sql: str) -> str:
    """Trim whitespace, strip a trailing semicolon and code fences."""
    s = (sql or "").strip()
    s = re.sub(r"^```(?:sql)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```$", "", s)
    return s.strip().rstrip(";").strip()


def _dynamic_blocklist() -> list:
    """Merge DB-configured restricted commands + custom keywords with the static list.

    Reads RestrictedSQLCommand rows (is_blocked) and the Setting 'restricted_keywords'
    (a list) configured in the Security tab. Safe if the DB/app context is absent.
    """
    blocked = set(_FORBIDDEN)
    try:
        from .models import RestrictedSQLCommand, Setting
        for row in RestrictedSQLCommand.query.filter_by(is_blocked=True).all():
            if row.command:
                blocked.add(row.command.upper())
        extra = Setting.get("restricted_keywords") or []
        if isinstance(extra, list):
            for kw in extra:
                if kw:
                    blocked.add(str(kw).upper())
    except Exception:
        # No app/DB context (e.g. unit test) — fall back to static list.
        pass
    return sorted(blocked)


def validate(sql: str) -> Tuple[bool, str]:
    """Return (is_safe, reason). Only a single read-only SELECT/WITH allowed.

    Uses the static forbidden list PLUS any DB-configured restricted commands /
    keywords from the Security tab.
    """
    if not sql or not sql.strip():
        return False, "Empty SQL."

    body = _strip_sql_comments(sanitize(sql))
    if not body:
        return False, "SQL contains only comments."

    inner = body.rstrip(";")
    if ";" in inner:
        return False, "Multiple SQL statements are not allowed."

    upper = body.upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return False, "Only read-only SELECT queries are allowed."

    for kw in _dynamic_blocklist():
        if re.search(rf"\b{re.escape(kw)}\b", upper):
            return False, f"Statement contains a restricted command/keyword: {kw}."

    return True, "ok"


def contains_restricted(text: str) -> Tuple[bool, str]:
    """Check whether a prompt contains a restricted command/keyword."""
    if not text or not text.strip():
        return False, ""
    upper = text.upper()
    for kw in _dynamic_blocklist():
        if re.search(rf"\b{re.escape(kw)}\b", upper):
            return True, kw
    return False, ""


def enforce_limit(sql: str, default_limit: int = DEFAULT_LIMIT) -> str:
    """Append a default LIMIT when the query has none (and isn't an aggregate-only).

    Skips adding LIMIT when the query clearly aggregates to a single row
    (e.g. a bare COUNT/SUM/AVG without GROUP BY) since that already returns one row.
    """
    body = sanitize(sql)
    upper = body.upper()

    if re.search(r"\bLIMIT\b", upper) or re.search(r"\bFETCH\s+FIRST\b", upper):
        return body  # already limited

    # If it's a single-row aggregate (no GROUP BY) don't force a LIMIT.
    has_group_by = "GROUP BY" in upper
    is_agg = re.search(r"\bSELECT\b\s+(COUNT|SUM|AVG|MIN|MAX)\s*\(", upper)
    if is_agg and not has_group_by:
        return body

    return f"{body}\nLIMIT {int(default_limit)}"


def _normalize_company_fk(company_fk) -> list:
    """Normalize a company_fk argument (int, str, or iterable) into a sorted list of ints."""
    if company_fk is None:
        return []
    if isinstance(company_fk, (list, tuple, set)):
        ids = []
        for v in company_fk:
            try:
                ids.append(int(v))
            except (ValueError, TypeError):
                continue
        return sorted(set(ids))
    try:
        return [int(company_fk)]
    except (ValueError, TypeError):
        return []


def enforce_company_fk(sql: str, company_fk) -> str:
    """Enforce company_fk filtering on the query.
    
    This is a MANDATORY enforcement that applies to all queries, regardless of
    what the LLM generated. Ensures users can never see data from other companies.
    
    Args:
        sql: The SQL query
        company_fk: The company's foreign key derived from the user's token. May be a
            single id (int) or a list of ids (parent company + its child branches),
            in which case a ``company_fk IN (...)`` filter is applied.
    
    Returns:
        Modified SQL with company_fk filter enforced
    """
    ids = _normalize_company_fk(company_fk)
    if not sql or not ids:
        return sql
    
    body = sanitize(sql).strip()
    upper = body.upper()
    
    id_set = set(ids)
    
    # Don't modify if it already has an equality filter restricted to one of the allowed ids.
    eq_matches = re.findall(r"COMPANY_FK\s*=\s*(\d+)", upper)
    if eq_matches and all(int(v) in id_set for v in eq_matches):
        logger.debug(f"Query already scoped to allowed company_fk {eq_matches}")
        return body
    
    # Don't modify if it already has an IN filter that is a subset of the allowed ids.
    in_matches = re.findall(r"COMPANY_FK\s+IN\s*\(([^)]+)\)", upper)
    if in_matches:
        in_ids = [int(v) for v in re.findall(r"\d+", in_matches[0])]
        if in_ids and all(v in id_set for v in in_ids):
            logger.debug(f"Query already scoped to allowed company_fk IN {in_ids}")
            return body
    
    # Build the filter clause: single id -> equality; multiple ids -> IN (...)
    if len(ids) == 1:
        filter_expr = f"company_fk = {ids[0]}"
    else:
        filter_expr = f"company_fk IN ({', '.join(str(i) for i in ids)})"
    
    # Determine if we need to add WHERE or AND
    has_where = " WHERE " in upper
    connector = " AND " if has_where else " WHERE "
    filter_clause = f"{connector}{filter_expr}"
    
    # Try to add before ORDER BY, LIMIT, etc.
    order_match = re.search(r"\b(ORDER\s+BY|LIMIT|OFFSET|FETCH|GROUP\s+BY)\b", upper)
    if order_match:
        # Insert before the first terminal clause
        insert_pos = body.upper().index(order_match.group(1))
        modified = body[:insert_pos].rstrip() + filter_clause + "\n" + body[insert_pos:]
    else:
        # Append at the end
        modified = body.rstrip() + filter_clause
    
    logger.info(f"Enforced {filter_expr} on query")
    return modified


def detect_wrong_company_fk(sql: str, user_company_fk) -> Tuple[bool, str]:
    """Detect if the query contains a hardcoded company_fk that is outside the user's allowed companies.
    
    This catches cases where the LLM hardcoded company_fk = 1 (or any wrong value) in the query.
    Such queries should be regenerated since they'll return 0 rows when we enforce the correct company_fk.
    
    Args:
        sql: The SQL query
        user_company_fk: The user's allowed company_fk — a single id (int) or a list of ids
            (parent company + its child branches).
    
    Returns:
        (has_wrong_company_fk, reason)
        - If query references a company_fk outside the allowed set: (True, "reason")
        - Otherwise: (False, "")
    """
    allowed = set(_normalize_company_fk(user_company_fk))
    if not sql or not allowed:
        return False, ""
    
    allowed_str = ", ".join(str(v) for v in sorted(allowed))
    body = sanitize(sql).strip()
    upper = body.upper()
    
    # Find all company_fk = <value> patterns
    matches = re.findall(rf"COMPANY_FK\s*=\s*(\d+)", upper, re.IGNORECASE)
    
    for match in matches:
        hardcoded_fk = int(match)
        if hardcoded_fk not in allowed:
            return True, f"Query has hardcoded company_fk = {hardcoded_fk}, but user's allowed company_fk is {allowed_str}. This would return 0 rows."
    
    # Also check for company_fk IN (...) patterns and detect if any value is outside the allowed set
    in_matches = re.findall(rf"COMPANY_FK\s+IN\s*\(([^)]+)\)", upper, re.IGNORECASE)
    for in_values in in_matches:
        # Extract individual values from the IN list
        values = re.findall(r"(\d+)", in_values)
        if values:
            values_set = set(int(v) for v in values)
            # If the IN list contains values outside the allowed set, it's wrong
            if not values_set.issubset(allowed):
                return True, f"Query has company_fk IN ({', '.join(str(v) for v in sorted(values_set))}), but user's allowed company_fk is {allowed_str}. This would leak or miss data."
    
    return False, ""


def sanitize_user_text(text: str) -> str:
    """Light prompt-injection sanitation for the incoming natural-language question."""
    if not text:
        return ""
    cleaned = text.strip()
    # Neutralize blatant instruction-override attempts (defense in depth; the
    # guard above is the real protection).
    patterns = [
        r"(?i)ignore (all|previous|above) instructions",
        r"(?i)disregard (the )?(system|previous) prompt",
        r"(?i)you are now",
        r"(?i)drop\s+table",
        r"(?i)delete\s+from",
    ]
    for p in patterns:
        cleaned = re.sub(p, "[filtered]", cleaned)
    return cleaned


def check_table_access(sql: str, user_roles: list = None) -> Tuple[bool, str]:
    """Check if user has access to all tables referenced in the SQL query.
    
    Args:
        sql: The SQL query to check
        user_roles: List of role NAMES the user has (e.g., ["USER", "ADMIN"]). 
                   Can be strings (role names from token) or integers (role IDs from admin DB).
                   If empty/None, only allows access to tables with no access restrictions.
    
    Returns:
        (is_allowed, reason) - (True, "") if allowed, (False, reason_string) if denied
    """
    if not sql or not sql.strip():
        return True, ""
    
    try:
        from .models import TableRoleAccess
        
        # Extract table names from SQL (simple regex-based extraction)
        # Handles: FROM table, JOIN table, INTO table, UPDATE table, etc.
        table_pattern = r'\b(?:FROM|JOIN|INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|CROSS\s+JOIN|FULL\s+JOIN|UPDATE|INTO)\s+(?:"?([a-zA-Z_][a-zA-Z0-9_]*))?'
        
        body = _strip_sql_comments(sanitize(sql))
        matches = re.finditer(table_pattern, body, re.IGNORECASE)
        
        tables_in_sql = set()
        for match in matches:
            table_name = match.group(1)
            if table_name:
                tables_in_sql.add(table_name.lower())
        
        if not tables_in_sql:
            # No tables found in query (shouldn't happen for SELECT)
            return True, ""
        
        # Normalize user roles to strings for comparison
        user_role_names = set()
        if user_roles:
            for role in user_roles:
                if isinstance(role, str):
                    user_role_names.add(role.upper())
                else:
                    # If it's an ID, try to look it up in admin DB
                    try:
                        from .models import Role as AdminRole
                        admin_role = AdminRole.query.get(role)
                        if admin_role:
                            user_role_names.add(admin_role.name.upper())
                    except Exception:
                        pass
        
        # For each table, check if user has access
        for table_name in tables_in_sql:
            # Get all role access records for this table
            accesses = TableRoleAccess.query.filter_by(table_name=table_name).all()
            
            if not accesses:
                # No access restrictions for this table - open to all users
                continue
            
            # Get role names that have access to this table
            allowed_role_names = set()
            for access in accesses:
                if access.role:
                    allowed_role_names.add(access.role.name.upper())
            
            if not allowed_role_names:
                # Table has access config but no roles found - deny by default
                continue
            
            # If table has access restrictions, user must have one of the allowed roles
            if user_role_names:
                if not user_role_names.intersection(allowed_role_names):
                    # User's roles don't match any allowed roles
                    role_list = ", ".join(sorted(allowed_role_names))
                    return False, f"Table '{table_name}' is restricted to roles: {role_list}"
            else:
                # User has no roles but table requires roles
                role_list = ", ".join(sorted(allowed_role_names))
                return False, f"Table '{table_name}' requires specific roles: {role_list}. Your user has no roles assigned."
        
        return True, ""
    
    except Exception as exc:
        logger.debug(f"Table access check failed (non-fatal): {exc}")
        # If access check fails, allow the query (err on side of permissiveness)
        # The database permissions layer will catch actual access violations
        return True, ""
