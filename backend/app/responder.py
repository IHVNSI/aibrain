"""Conversational response composer.

After Vanna generates + runs SQL, this turns the raw result rows into a
human-readable answer that follows the SAME response guide as the companion
`brainz` project (see app/response_guide.py — copied verbatim). This ensures
both apps "respond to questions" identically: conversational, no raw data
dumps, with interpretation and suggested next steps.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from .response_guide import CLIENTSHOT_SYSTEM_INSTRUCTIONS

logger = logging.getLogger(__name__)

MAX_ROWS_FOR_LLM = 30


def get_system_instructions(intent: str = "database_query") -> str:
    """Get system instructions from database, optionally with intent-specific rules.
    
    Args:
        intent: The type of request - 'database_query', 'send_email', 'send_whatsapp', etc.
    
    Returns:
        System instructions string, possibly with intent-specific rules appended.
    """
    try:
        from .models import AIContext
        active_context = AIContext.get_active()
        if active_context and active_context.system_instructions:
            instructions = active_context.system_instructions
            
            # Append intent-specific rules if available
            if intent == "send_email" and active_context.email_response_rules:
                instructions += f"\n\n[EMAIL-SPECIFIC RULES]\n{active_context.email_response_rules}"
            elif intent == "send_whatsapp" and active_context.whatsapp_response_rules:
                instructions += f"\n\n[WHATSAPP-SPECIFIC RULES]\n{active_context.whatsapp_response_rules}"
            
            return instructions
    except Exception as e:
        logger.warning(f"Could not load AI context from database: {e}")
    
    # Fall back to hardcoded default
    return CLIENTSHOT_SYSTEM_INSTRUCTIONS


def compose_answer(llm, user_query: str, sql: str, columns: List[str],
                   rows: List[Dict[str, Any]], row_count: int,
                   run_error: Optional[str] = None, intent: str = "database_query") -> Optional[str]:
    """Return a conversational answer string, or None to fall back to a default.

    Uses the shared response guide as the system prompt so the tone/rules match
    the brainz app exactly. If intent is provided, appends intent-specific rules.
    
    Args:
        llm: Language model instance
        user_query: The user's original query
        sql: The SQL that was generated/executed
        columns: List of column names from the result
        rows: List of result rows
        row_count: Total number of rows returned (or affected for DML operations)
        run_error: Optional error message if SQL execution failed
        intent: Type of request ('database_query', 'send_email', 'send_whatsapp', etc.)
    
    Returns:
        A conversational answer string or None
    """
    if llm is None:
        return None

    # Detect if this is a DML operation (no rows/columns returned, but affected_rows in row_count)
    is_dml = not rows and not columns and row_count > 0
    sql_upper = sql.strip().upper()
    is_insert = sql_upper.startswith("INSERT")
    is_update = sql_upper.startswith("UPDATE")
    is_delete = sql_upper.startswith("DELETE")

    if run_error:
        error_lower = run_error.lower()
        # Detect timeout errors and provide specific guidance
        if 'timeout' in error_lower or 'timed out' in error_lower:
            situation = (
                f"The user asked: {user_query}\n\n"
                f"The database query timed out because it was too complex or slow.\n"
                f"Error: {run_error}\n\n"
                f"SQL attempted:\n{sql}\n\n"
                "Explain that the query timed out due to complexity/size, and suggest: "
                "1. Try asking for a more specific customer/time period, "
                "2. Ask for fewer columns or simpler calculations, "
                "3. Mention that the system will try a simpler query if they refine their request."
            )
        else:
            situation = (
                f"The generated SQL failed to execute with this error:\n{run_error}\n\n"
                f"SQL attempted:\n{sql}\n\n"
                "Explain the problem in plain English and suggest how the user could rephrase."
            )
    elif is_dml:
        # DML operation - no rows returned, but affected_rows count in row_count
        operation = "inserted" if is_insert else ("updated" if is_update else "deleted")
        situation = (
            f"The user asked: {user_query}\n\n"
            f"SQL that was run (for your reference only — do NOT show it unless asked):\n{sql}\n\n"
            f"Result: Successfully {operation} {row_count} row(s).\n\n"
            "Write a conversational acknowledgment of the successful operation. "
            "Be encouraging and friendly. Do NOT show the raw SQL unless asked."
        )
    else:
        # SELECT query - rows returned
        sample = rows[:MAX_ROWS_FOR_LLM]
        try:
            sample_json = json.dumps(sample, default=str, indent=2)
        except Exception:
            sample_json = str(sample)
        situation = (
            f"The user asked: {user_query}\n\n"
            f"SQL that was run (for your reference only — do NOT show it unless asked):\n{sql}\n\n"
            f"Total rows returned: {row_count}\n"
            f"Columns: {', '.join(columns) if columns else '(none)'}\n"
            f"Result sample (up to {MAX_ROWS_FOR_LLM} rows):\n{sample_json}\n\n"
            "Write a conversational answer that interprets these results per the rules above. "
            "Do NOT dump raw tables or field names; explain what the data means and suggest a next step."
        )

    try:
        system_instructions = get_system_instructions(intent=intent)
        text = llm.chat([
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": situation},
        ])
        return (text or "").strip() or None
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Conversational responder failed: {exc}")
        return None
