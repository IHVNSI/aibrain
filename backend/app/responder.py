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


def get_system_instructions() -> str:
    """Get system instructions from database or fall back to default."""
    try:
        from .models import AIContext
        active_context = AIContext.get_active()
        if active_context and active_context.system_instructions:
            return active_context.system_instructions
    except Exception as e:
        logger.warning(f"Could not load AI context from database: {e}")
    
    # Fall back to hardcoded default
    return CLIENTSHOT_SYSTEM_INSTRUCTIONS


def compose_answer(llm, user_query: str, sql: str, columns: List[str],
                   rows: List[Dict[str, Any]], row_count: int,
                   run_error: Optional[str] = None) -> Optional[str]:
    """Return a conversational answer string, or None to fall back to a default.

    Uses the shared response guide as the system prompt so the tone/rules match
    the brainz app exactly.
    """
    if llm is None:
        return None

    if run_error:
        situation = (
            f"The generated SQL failed to execute with this error:\n{run_error}\n\n"
            f"SQL attempted:\n{sql}\n\n"
            "Explain the problem in plain English and suggest how the user could rephrase."
        )
    else:
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
        system_instructions = get_system_instructions()
        text = llm.chat([
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": situation},
        ])
        return (text or "").strip() or None
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Conversational responder failed: {exc}")
        return None
