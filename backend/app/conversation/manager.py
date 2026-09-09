"""Multi-turn conversation manager.

SQLite (Conversation model) is the authoritative store. This module also
performs cumulative prompt consolidation: every new prompt is treated as a
modification/continuation of the prior turns and folded into ONE self-contained
question before it reaches Vanna for SQL generation.
"""
import json
import logging
import re
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from ..extensions import db
from ..models import Conversation

logger = logging.getLogger(__name__)

MAX_TURNS = 24


class ConversationManager:
    # ------------------------------------------------------------------ #
    # Persistence (SQLite is source of truth)
    # ------------------------------------------------------------------ #
    @staticmethod
    def new_id() -> str:
        return f"conv_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def get(conversation_id: str) -> Optional[Conversation]:
        return Conversation.query.filter_by(conversation_id=conversation_id).first()

    @staticmethod
    def list() -> List[Conversation]:
        return Conversation.query.order_by(Conversation.updated_at.desc()).all()

    @staticmethod
    def history(conversation_id: str) -> List[Dict[str, Any]]:
        conv = ConversationManager.get(conversation_id)
        return conv.get_messages() if conv else []

    @staticmethod
    def append_turn(conversation_id: str, user_query: str, answer: Dict[str, Any],
                    title_hint: str = "", user_id: Optional[int] = None,
                    is_first_message: bool = False, message_position: int = 1) -> Conversation:
        conv = ConversationManager.get(conversation_id)
        now = datetime.utcnow()
        user_msg = {
            "type": "user",
            "content": user_query,
            "ts": now.isoformat(),
            "is_first_message": is_first_message,
            "message_position": message_position,
        }
        ai_msg = {
            "type": "ai",
            "content": answer.get("message", ""),
            "sql_query": answer.get("sql_query", ""),
            "row_count": answer.get("row_count", 0),
            "columns": answer.get("columns"),
            "data": answer.get("data"),
            "visualization": answer.get("visualization"),
            "trend": answer.get("trend"),
            "insights": answer.get("insights"),
            "corrections": answer.get("corrections"),
            "rewritten_query": answer.get("rewritten_query"),
            "rewrite_info": answer.get("rewrite_info"),
            "error": answer.get("error"),
            "success": answer.get("success"),
            "llm_provider": answer.get("llm_provider"),
            "llm_model": answer.get("llm_model"),
            "ts": now.isoformat(),
            "is_first_message": is_first_message,
            "message_position": message_position,
        }
        if conv:
            msgs = conv.get_messages()
            msgs.extend([user_msg, ai_msg])
            conv.messages = json.dumps(msgs[-(MAX_TURNS * 2):])
            conv.updated_at = now
        else:
            title = (title_hint or user_query or "New conversation").strip()[:80]
            conv = Conversation(
                conversation_id=conversation_id,
                user_id=user_id,
                title=title,
                messages=json.dumps([user_msg, ai_msg]),
            )
            db.session.add(conv)
        db.session.commit()
        return conv

    @staticmethod
    def delete(conversation_id: str) -> bool:
        conv = ConversationManager.get(conversation_id)
        if not conv:
            return False
        db.session.delete(conv)
        db.session.commit()
        return True

    @staticmethod
    def rename(conversation_id: str, title: str) -> Optional[Conversation]:
        conv = ConversationManager.get(conversation_id)
        if not conv:
            return None
        conv.title = title.strip()[:300]
        db.session.commit()
        return conv

    @staticmethod
    def update_messages(conversation_id: str, messages: List[Dict[str, Any]]) -> Optional[Conversation]:
        conv = ConversationManager.get(conversation_id)
        if not conv:
            return None
        cleaned = messages[-(MAX_TURNS * 2):] if messages else []
        conv.messages = json.dumps(cleaned)
        conv.updated_at = datetime.utcnow()
        db.session.commit()
        return conv

    # ------------------------------------------------------------------ #
    # Cumulative prompt consolidation (continuation-first, LLM-driven)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _prior_user_prompts(history: List[Dict[str, Any]]) -> List[str]:
        return [m.get("content", "") for m in (history or [])
                if m.get("type") == "user" and m.get("content")]

    @staticmethod
    def _transcript(history: List[Dict[str, Any]], max_msgs: int = MAX_TURNS) -> str:
        lines = []
        turn = 0
        for m in (history or [])[-max_msgs:]:
            if m.get("type") == "user":
                turn += 1
                lines.append(f"\n--- Turn {turn} ---")
                lines.append(f"USER asked: {m.get('content','')}")
            elif m.get("type") == "ai":
                lines.append(f"ASSISTANT answered: {m.get('content','')}")
                if m.get("sql_query"):
                    lines.append(f"    [SQL generated (reference only): {m['sql_query']}]")
        return "\n".join(lines)

    @staticmethod
    def consolidate(current_query: str, history: List[Dict[str, Any]], llm) -> Tuple[str, Dict[str, Any]]:
        """Fold the chain of prior prompts + the newest into ONE merged request.

        Returns (consolidated_query, info). Falls back to the original query when
        there is no history or no LLM.
        """
        info = {"modified": False, "prior_prompts": 0, "engine": getattr(llm, "name", "none"),
                "reason": ""}
        if not current_query or not current_query.strip():
            info["reason"] = "empty_query"
            return current_query, info

        prior = ConversationManager._prior_user_prompts(history)
        info["prior_prompts"] = len(prior)
        if not prior:
            info["reason"] = "no_prior_prompts"
            return current_query, info
        if llm is None:
            info["reason"] = "no_llm"
            return current_query, info

        numbered = "\n".join(f"{i}. {p}" for i, p in enumerate(prior, 1))
        transcript = ConversationManager._transcript(history)
        system = (
            "You merge a multi-turn data-analytics conversation into ONE complete, "
            "self-contained request. The newest request is a MODIFICATION of the "
            "earlier ones (expand / narrow / filter / re-time / re-sort). Carry "
            "forward every still-relevant entity, table, filter, time period and "
            "sort order; the NEWEST request wins on conflicts. Resolve 'these', "
            "'those', 'them', 'that' using the earlier requests. You decide if the "
            "subject changed. Do NOT invent tables/columns. Return ONLY a JSON "
            'object: {"consolidated_query": "...", "modified": true|false}.'
        )
        user = (
            f"Previous requests:\n{numbered}\n\n"
            f"Conversation transcript:\n{transcript}\n\n"
            f"Newest request:\n{current_query}\n\n"
            "Output JSON only:"
        )
        try:
            raw = llm.chat([
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ])
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Consolidation LLM call failed: {exc}")
            info["reason"] = f"llm_error:{type(exc).__name__}"
            return current_query, info

        parsed = ConversationManager._extract_json(raw)
        consolidated = (parsed or {}).get("consolidated_query") if parsed else None
        if not isinstance(consolidated, str) or not consolidated.strip():
            # Some small models just emit the merged text without JSON — use it if sane.
            candidate = (raw or "").strip()
            if candidate and len(candidate) < 600 and "\n" not in candidate[:400]:
                consolidated = candidate
            else:
                info["reason"] = "unparseable"
                return current_query, info

        consolidated = consolidated.strip()
        if consolidated == current_query.strip():
            info["reason"] = "unchanged"
            return current_query, info

        info["modified"] = True
        info["reason"] = "consolidated"
        # Prominent log so the rewritten multi-turn prompt is visible in terminal/logs.
        logger.warning("=" * 90)
        logger.warning("🧩 MULTI-TURN PROMPT REWRITTEN (engine=%s)", info["engine"])
        logger.warning("=" * 90)
        for i, p in enumerate(prior, 1):
            logger.warning("   prior[%d]: %s", i, p)
        logger.warning("   NEWEST   : %s", current_query)
        logger.warning("   ➡️  REWRITTEN PROMPT SENT TO VANNA: %s", consolidated)
        logger.warning("=" * 90)
        return consolidated, info

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except Exception:
            pass
        m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
