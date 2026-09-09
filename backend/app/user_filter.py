"""User-based query filtering - apply company and branch filters to SQL queries."""
import logging
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class UserQueryFilter:
    """
    Applies company and branch filters to SQL queries based on current user context.

    Rules:
    - Regular users can only see data for their assigned company and branch
    - If branch_id is None, user can see all branches of their company
    - Admin users can see everything
    - Filter based on tables with company_fk, company_id, branch_fk, branch_id columns
    """

    def __init__(
        self,
        user_id: int,
        company_id: Optional[int],
        branch_id: Optional[int] = None,
        is_admin: bool = False,
        related_company_ids: Optional[list] = None,
    ):
        self.user_id = user_id
        self.company_id = company_id
        self.branch_id = branch_id
        self.is_admin = is_admin

        ids = set()
        if company_id is not None:
            try:
                ids.add(int(company_id))
            except (TypeError, ValueError):
                pass
        for cid in related_company_ids or []:
            try:
                ids.add(int(cid))
            except (TypeError, ValueError):
                pass
        self.related_company_ids = sorted(ids)

    def get_company_filter_sql(self, table_alias: str = "") -> str:
        if self.is_admin or not self.company_id:
            return ""

        prefix = f"{table_alias}." if table_alias else ""
        ids = self.related_company_ids or [int(self.company_id)]

        if len(ids) == 1:
            rhs_id = ids[0]
            return f"({prefix}company_fk = {rhs_id} OR {prefix}company_id = {rhs_id})"
        id_list = ", ".join(str(i) for i in ids)
        return f"({prefix}company_fk IN ({id_list}) OR {prefix}company_id IN ({id_list}))"

    def get_branch_filter_sql(self, table_alias: str = "") -> str:
        if self.is_admin or not self.branch_id:
            return ""

        prefix = f"{table_alias}." if table_alias else ""
        return (
            f"({prefix}branch_fk = {self.branch_id} OR "
            f"{prefix}branch_id = {self.branch_id} OR "
            f"{prefix}service_point_id = {self.branch_id})"
        )

    def build_combined_filter(self, table_alias: str = "", require_branch: bool = False) -> str:
        if self.is_admin:
            return ""

        filters = []
        if not require_branch:
            company_filter = self.get_company_filter_sql(table_alias)
            if company_filter:
                filters.append(company_filter)

        if self.branch_id:
            branch_filter = self.get_branch_filter_sql(table_alias)
            if branch_filter:
                filters.append(branch_filter)

        if not filters:
            return ""

        return " AND ".join(filters)

    def modify_sql_query(self, sql_query: str, table_mappings: Dict[str, str] = None) -> str:
        if self.is_admin or not sql_query:
            return sql_query

        try:
            query = sql_query.strip()

            if query.upper().startswith("SELECT"):
                return self._modify_select_query(query, table_mappings)
            if query.upper().startswith("WITH"):
                return self._modify_with_query(query, table_mappings)

            return query
        except Exception as exc:
            logger.warning(f"Could not modify query for user filtering: {exc}")
            return sql_query

    def _modify_select_query(self, query: str, table_mappings: Dict[str, str] = None) -> str:
        where_match = re.search(r"\bWHERE\b", query, re.IGNORECASE)
        filter_sql = self._get_default_filter_sql(table_mappings)

        if not filter_sql:
            return query

        if where_match:
            # Insert after WHERE keyword, not before
            insert_pos = where_match.end()
            return query[:insert_pos] + f" ({filter_sql}) AND" + query[insert_pos:]

        return query + f" WHERE {filter_sql}"

    def _modify_with_query(self, query: str, table_mappings: Dict[str, str] = None) -> str:
        main_select_match = re.search(r"SELECT\s+", query, re.IGNORECASE)
        if not main_select_match:
            return query

        filter_sql = self._get_default_filter_sql(table_mappings)
        if not filter_sql:
            return query

        where_match = re.search(r"\bWHERE\b", query[main_select_match.end():], re.IGNORECASE)
        if where_match:
            # Insert after WHERE keyword, not before
            insert_pos = main_select_match.end() + where_match.end()
            return query[:insert_pos] + f" ({filter_sql}) AND" + query[insert_pos:]

        return query + f" WHERE {filter_sql}"

    def _get_default_filter_sql(self, table_mappings: Dict[str, str] = None) -> str:
        if self.is_admin:
            return ""

        if not table_mappings:
            if self.branch_id:
                return self.build_combined_filter()
            return self.get_company_filter_sql()

        filters = []
        for table_name, column_name in table_mappings.items():
            if column_name is None:
                continue
            if self.branch_id:
                table_filter = self.build_combined_filter(table_name)
            else:
                table_filter = self.get_company_filter_sql(table_name)
            if table_filter:
                filters.append(table_filter)

        return " AND ".join(filters)
