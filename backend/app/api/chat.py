"""Chat API: multi-turn conversational text-to-SQL via Vanna."""
import json
import logging
import time
import re
import os

from flask import Blueprint, request, jsonify

from ..extensions import db
from ..models import AuditLog, AuditLogDetail, User
from ..conversation import ConversationManager
from ..vanna_service import get_vanna_service
from ..llm import build_llm, get_llm_settings
from .. import sql_guard
from ..analysis import analyze
from ..auth import require_auth, current_user_context
from ..user_filter import UserQueryFilter

logger = logging.getLogger(__name__)
chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")

MAX_CORRECTION_ATTEMPTS = 2


def _is_api_request():
    """
    Detect if request came from API client (Postman, curl, etc.) vs web UI.
    
    Criteria:
    - Postman user-agent
    - curl user-agent
    - X-API-Request: true header
    - Accept: application/json without text/html
    """
    user_agent = request.headers.get("User-Agent", "").lower()
    if "postman" in user_agent or "curl" in user_agent:
        return True
    
    if request.headers.get("X-API-Request", "").lower() in ("true", "1", "yes"):
        return True
    
    accept = request.headers.get("Accept", "")
    # If accept doesn't include text/html, likely an API client
    if "application/json" in accept and "text/html" not in accept:
        return True
    
    return False


def _usage_snapshot(llm_obj):
    usage = getattr(llm_obj, "last_usage", None)
    if isinstance(usage, dict):
        return {
            "input_tokens": int(usage.get("input_tokens", 0) or 0),
            "output_tokens": int(usage.get("output_tokens", 0) or 0),
            "cache_creation_input_tokens": int(usage.get("cache_creation_input_tokens", 0) or 0),
            "cache_read_input_tokens": int(usage.get("cache_read_input_tokens", 0) or 0),
        }
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }


def _merge_usage(*chunks):
    merged = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    for c in chunks:
        if not isinstance(c, dict):
            continue
        merged["input_tokens"] += int(c.get("input_tokens", 0) or 0)
        merged["output_tokens"] += int(c.get("output_tokens", 0) or 0)
        merged["cache_creation_input_tokens"] += int(c.get("cache_creation_input_tokens", 0) or 0)
        merged["cache_read_input_tokens"] += int(c.get("cache_read_input_tokens", 0) or 0)
    return merged


def _company_filter_ids(ctx: dict) -> list:
    """Return the list of company ids a user is allowed to see (for data isolation).

    Prefers ``related_company_ids`` (parent company + its child branches, resolved
    from the SOURCE database). Falls back to the single ``company_fk`` then
    ``company_id``. Returns an empty list for admins or when no scope is known.
    """
    if not ctx or ctx.get("is_admin"):
        return []
    related = ctx.get("related_company_ids") or []
    ids = [int(i) for i in related if i is not None] if related else []
    primary = ctx.get("company_fk") or ctx.get("company_id")
    if primary is not None:
        try:
            primary = int(primary)
            if primary not in ids:
                ids.append(primary)
        except (ValueError, TypeError):
            pass
    return sorted(set(ids))


def _build_scope_note(ctx: dict) -> str:
    """Build a data-isolation instruction limiting results to the user's company
    (and branch). Admins see everything. Vanna still decides HOW to write the SQL;
    this only constrains the WHERE scope."""
    if not ctx or ctx.get("is_admin"):
        return ""
    # Use company_fk if available, otherwise fall back to company_id
    company_fk = ctx.get("company_fk") or ctx.get("company_id")
    branch_id = ctx.get("branch_id")
    if not company_fk and not branch_id:
        return ""
    parts = [
        "DATA ISOLATION (MANDATORY): The logged-in user may ONLY see their own "
        "organization's data. When the target table has a foreign key column "
        "like company_fk, company_id, organization_id, or similar, you MUST filter by it."
    ]
    related_ids = ctx.get("related_company_ids") or []
    
    # Use company_fk (already has fallback to company_id above)
    filter_id = company_fk
    if not filter_id:
        return ""
    
    if related_ids:
        id_list = ", ".join(str(i) for i in related_ids)
        parts.append(
            f"- Restrict to company_fk IN ({id_list}) "
            "wherever a company_fk column exists."
        )
        parts.append(
            f"- OR restrict to company_id IN ({id_list}) "
            "if company_fk does not exist."
        )
    else:
        parts.append(
            f"- Restrict to company_fk = {filter_id} "
            "wherever a company_fk column exists (preferred for FK relationships)."
        )
        parts.append(
            f"- OR restrict to company_id = {filter_id} "
            "if company_fk does not exist."
        )
    if branch_id:
        parts.append(
            f"- Also restrict to branch_fk = {branch_id} or branch_id = {branch_id} "
            f"wherever a branch column exists."
        )
    parts.append("Never return rows belonging to other companies or branches.")
    return "\n".join(parts)


def _training_access_mode(ctx: dict) -> str:
    username = (ctx or {}).get("username")
    if isinstance(username, str) and username.strip().lower() == "guest":
        return "guest"
    return "authenticated"


def _extract_json(text: str):
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


def _route_query(llm, question: str, history):
    if llm is None:
        return {"mode": "database", "reason": "no_llm_router"}

    transcript = "\n".join([
        f"{m.get('type', '').upper()}: {m.get('content', '')}"
        for m in (history or [])[-8:]
    ])
    prompt = (
        "Route the latest user request for an analytics assistant. "
        "Choose EXACTLY one mode: database, knowledge_base, or direct. "
        "Priority rule: if the request can be answered from business data/records/tables/metrics/counts/trends, "
        "choose database. If the user asks policy/document/how-to/manual content, choose knowledge_base. "
        "Use direct only for greetings/chitchat/general non-data replies. "
        "When uncertain between database and other modes, choose database. "
        "Return only JSON: {\"mode\":\"database|knowledge_base|direct\",\"reason\":\"short reason\"}."
    )
    try:
        raw = llm.chat([
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Conversation context:\n{transcript}\n\nLatest request:\n{question}"},
        ])
        parsed = _extract_json(raw) or {}
        mode = str(parsed.get("mode") or "database").strip().lower()
        if mode not in {"database", "knowledge_base", "direct"}:
            mode = "database"
        return {"mode": mode, "reason": str(parsed.get("reason") or "")}
    except Exception:
        return {"mode": "database", "reason": "router_error"}


def _answer_knowledge_base(llm, svc, question: str, access_mode: str):
    docs = svc.get_related_knowledge(question, access_mode=access_mode, limit=8)
    if not docs:
        return (
            "I could not find a matching knowledge base entry for this request. "
            "Please upload relevant documents in the Knowledge Base section or rephrase your question.",
            0,
        )

    context = "\n\n---\n\n".join(docs)
    if len(context) > 16000:
        context = context[:16000]

    text = llm.chat([
        {
            "role": "system",
            "content": (
                "You answer using the provided knowledge base context first. "
                "If context is insufficient, say so clearly and ask for more details. "
                "Do not fabricate facts beyond context."
            ),
        },
        {
            "role": "user",
            "content": f"Knowledge base context:\n{context}\n\nQuestion:\n{question}",
        },
    ])
    return (text or "").strip() or "I could not generate a knowledge base answer.", len(docs)


def _answer_direct(llm, question: str):
    if llm is None:
        return "I can help with data questions, knowledge base questions, or general guidance."
    text = llm.chat([
        {"role": "system", "content": "You are a concise and helpful assistant."},
        {"role": "user", "content": question},
    ])
    return (text or "").strip() or "I can help with that."


def _execute(svc, sql):
    """Run SQL; return (rows, columns, row_count, error)."""
    try:
        df = svc.run_sql(sql)
        if df is None:
            return [], [], 0, None
        cols = list(df.columns)
        rows = df.head(500).to_dict(orient="records")
        return rows, cols, int(len(df)), None
    except Exception as exc:  # noqa: BLE001
        return [], [], 0, str(exc)


@chat_bp.route("/query", methods=["POST"])
@chat_bp.route("/query/guest", methods=["POST"])
@require_auth
def query():
    """Generate + run SQL for a question, treating it as a continuation of the
    conversation. Implements: RAG schema/few-shot (Vanna) -> CoT prompt ->
    safety guard (SELECT-only + LIMIT) -> execute with self-correction loop ->
    analysis (chart/trend/insights) -> conversational answer.
    Body: { query or message, conversation_id?, is_first_message? }."""
    data = request.get_json(silent=True) or {}
    # Accept both 'query' and 'message' for flexibility
    raw_query = (data.get("query") or data.get("message") or "").strip()
    # Guardrail: sanitize incoming text against prompt-injection.
    user_query = sql_guard.sanitize_user_text(raw_query)
    conversation_id = data.get("conversation_id") or ConversationManager.new_id()
    # Track if this is the first message in the conversation
    is_first_message = data.get("is_first_message", False)
    if not conversation_id or not ConversationManager.get(conversation_id):
        is_first_message = True

    if not user_query:
        return jsonify({"success": False, "error": "Missing 'query' or 'message'"}), 400

    ctx = current_user_context()
    is_api = _is_api_request()
    user_id = ctx.get("user_id") if ctx else None
    username, role_name = _get_audit_user_info(ctx)
    
    # Calculate message position early (used in error paths)
    history = ConversationManager.history(conversation_id)
    message_position = len([m for m in history if m.get("type") == "user"]) + 1
    
    # Block guest users from accessing main query endpoint (use /query/guest instead)
    if request.path == "/api/chat/query" or (not request.path.endswith("/query/guest")):
        if (ctx.get("username") or "").strip().lower() == "guest":
            return jsonify({
                "success": False,
                "error": "Guest users cannot access database queries. Please log in with your credentials.",
                "conversation_id": conversation_id,
            }), 403
    
    if request.path.endswith("/query/guest"):
        if (ctx.get("username") or "").strip().lower() != "guest":
            return jsonify({"success": False, "error": "This route is only accessible to the guest user."}), 403

    blocked, keyword = sql_guard.contains_restricted(user_query)
    if blocked:
        error_msg = f"Your request contains a restricted keyword or command. Please rephrase."
        error_answer = {
            "message": error_msg,
            "sql_query": "",
            "row_count": 0,
        }
        ConversationManager.append_turn(conversation_id, user_query, error_answer, title_hint=user_query, user_id=user_id, is_first_message=is_first_message, message_position=message_position)
        _audit(conversation_id, user_query, "", "", 0, success=False, error=f"Blocked: {keyword}",
               is_api=is_api, user_id=user_id, username=username, role_name=role_name)
        return jsonify({
            "success": False,
            "error": f"Blocked: restricted keyword/command detected ({keyword}).",
            "message": error_msg,
            "conversation_id": conversation_id,
        }), 400

    svc = get_vanna_service()
    if not svc.ready:
        from ..bootstrap import reinitialize_vanna
        status = reinitialize_vanna()
        if not svc.ready:
            return jsonify({
                "success": False,
                "error": status.get("error", "Text-to-SQL engine not ready. Configure LLM and database in Settings."),
                "conversation_id": conversation_id,
            }), 503

    started = time.time()
    correction_log = []

    # ----- Multi-turn: fold prior prompts into one consolidated request ----- #
    llm = build_llm(get_llm_settings())
    consolidated, info = ConversationManager.consolidate(user_query, history, llm)
    rewrite_usage = _usage_snapshot(llm)

    blocked, keyword = sql_guard.contains_restricted(consolidated)
    if blocked:
        error_msg = f"Your request contains a restricted keyword or command. Please rephrase."
        error_answer = {
            "message": error_msg,
            "sql_query": "",
            "row_count": 0,
        }
        ConversationManager.append_turn(conversation_id, user_query, error_answer, title_hint=user_query, user_id=user_id, is_first_message=is_first_message, message_position=message_position)
        return jsonify({
            "success": False,
            "error": f"Blocked: restricted keyword/command detected ({keyword}).",
            "message": error_msg,
            "conversation_id": conversation_id,
            "rewritten_query": consolidated,
        }), 400

    # ----- Route intent: database (priority), knowledge base, or direct ----- #
    user_ctx = current_user_context()
    access_mode = _training_access_mode(user_ctx)
    route_decision = _route_query(llm, consolidated, history)
    route_mode = route_decision.get("mode") or "database"
    routing_usage = _usage_snapshot(llm)

    if route_mode != "database":
        if route_mode == "knowledge_base":
            message, kb_hits = _answer_knowledge_base(llm, svc, consolidated, access_mode)
            context_cache = {"knowledge_docs_used": kb_hits}
        else:
            message = _answer_direct(llm, consolidated)
            context_cache = {"knowledge_docs_used": 0}

        response_usage = _usage_snapshot(llm)
        token_usage = {
            "rewrite": rewrite_usage,
            "routing": routing_usage,
            "response": response_usage,
            "total": _merge_usage(rewrite_usage, routing_usage, response_usage),
        }
        answer = {
            "message": message,
            "sql_query": "",
            "row_count": 0,
        }
        ConversationManager.append_turn(conversation_id, user_query, answer, title_hint=user_query, user_id=user_id, is_first_message=is_first_message, message_position=message_position)

        llm_settings = get_llm_settings()
        total_usage = token_usage["total"]
        _audit(
            conversation_id,
            user_query,
            consolidated,
            "",
            0,
            success=True,
            error=None,
            duration_ms=int((time.time() - started) * 1000),
            provider=llm_settings.get("provider"),
            model=llm_settings.get("model"),
            response_text=message,
            context_cache=context_cache,
            token_usage=token_usage,
            token_input=total_usage.get("input_tokens", 0),
            token_output=total_usage.get("output_tokens", 0),
            cache_creation_tokens=total_usage.get("cache_creation_input_tokens", 0),
            cache_read_tokens=total_usage.get("cache_read_input_tokens", 0),
            is_api=is_api,
            user_id=user_id,
            username=username,
            role_name=role_name,
        )

        return jsonify({
            "success": True,
            "conversation_id": conversation_id,
            "query": user_query,
            "rewritten_query": consolidated,
            "rewrite_info": info,
            "route": route_mode,
            "route_reason": route_decision.get("reason"),
            "sql_query": "",
            "columns": [],
            "data": [],
            "row_count": 0,
            "message": message,
            "error": None,
            "visualization": {"type": "text", "columns": []},
            "trend": None,
            "insights": [],
            "corrections": [],
            "llm_provider": llm_settings.get("provider"),
            "llm_model": llm_settings.get("model"),
            "duration_ms": int((time.time() - started) * 1000),
            "token_usage": token_usage,
            "context_cache": context_cache,
            "is_first_message": is_first_message,
            "message_position": message_position,
        }), 200

    # ----- Generate SQL with RAG + conversation context + CoT ----- #
    scope_note = _build_scope_note(user_ctx)
    try:
        sql = svc.generate_sql_multiturn(consolidated, history, scope_note=scope_note, access_mode=access_mode)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"SQL generation failed: {exc}")
        _audit(conversation_id, user_query, consolidated, "", 0, success=False, error=str(exc),
               duration_ms=int((time.time() - started) * 1000),
               context_cache=getattr(svc, "last_context_cache", {}),
               token_usage=rewrite_usage,
               token_input=rewrite_usage.get("input_tokens", 0),
               token_output=rewrite_usage.get("output_tokens", 0),
               cache_creation_tokens=rewrite_usage.get("cache_creation_input_tokens", 0),
               cache_read_tokens=rewrite_usage.get("cache_read_input_tokens", 0),
               is_api=is_api, user_id=user_id, username=username, role_name=role_name)
        return jsonify({
            "success": False, "error": f"SQL generation failed: {exc}",
            "conversation_id": conversation_id, "rewritten_query": consolidated,
        }), 500
    sql_usage = _usage_snapshot(getattr(svc, "_llm", None))

    # ----- Enforce company scope before validation ----- #
    sql = sql_guard.sanitize(sql)
    ctx = current_user_context()
    if ctx and not ctx.get("is_admin") and (ctx.get("company_id") or ctx.get("related_company_ids")):
        user_filter = UserQueryFilter(
            user_id=ctx.get("user_id"),
            company_id=ctx.get("company_id"),
            branch_id=ctx.get("branch_id"),
            is_admin=ctx.get("is_admin"),
            related_company_ids=ctx.get("related_company_ids") or [],
        )
        sql = user_filter.modify_sql_query(sql)

    # ----- Safety guard: SELECT-only + enforce default LIMIT ----- #
    safe, reason = sql_guard.validate(sql)
    if not safe:
        logger.warning(f"🛡️  Blocked unsafe SQL: {reason} | {sql}")
        _audit(conversation_id, user_query, consolidated, sql, 0, success=False,
               error=f"Blocked: {reason}", duration_ms=int((time.time() - started) * 1000),
               is_api=is_api, user_id=user_id, username=username, role_name=role_name)
        error_msg = "Apologies, I did not understand your last question/prompt, kindly provide more context or rephrase the question entirely to enable me provide a quality response. Thank you!"
        error_answer = {
            "message": error_msg,
            "sql_query": sql,
            "row_count": 0,
        }
        ConversationManager.append_turn(conversation_id, user_query, error_answer, title_hint=user_query, user_id=user_id, is_first_message=is_first_message, message_position=message_position)
        return jsonify({
            "success": False,
            "conversation_id": conversation_id,
            "rewritten_query": consolidated,
            "sql_query": sql,
            "error": f"The generated query was blocked for safety: {reason}",
            "message": error_msg,
        }), 200

    # ----- Table-level access control: check if user can access tables in the query ----- #
    user_role_names = []
    if ctx:
        # First, try to get roles from token context (for microservice/external auth)
        token_roles = ctx.get("roles") or []
        if token_roles:
            # Token has explicit roles list
            user_role_names = [str(r) for r in token_roles]
        else:
            # Fall back to admin DB user roles
            user = User.query.get(ctx.get("user_id"))
            if user:
                user_role_names = [r.name for r in user.roles()]
    
    table_access_ok, table_access_reason = sql_guard.check_table_access(sql, user_role_names)
    if not table_access_ok:
        logger.warning(f"🚫 Table access denied: {table_access_reason} | {sql}")
        _audit(conversation_id, user_query, consolidated, sql, 0, success=False,
               error=f"Table access denied: {table_access_reason}", duration_ms=int((time.time() - started) * 1000),
               is_api=is_api, user_id=user_id, username=username, role_name=role_name)
        error_msg = f"You do not have access to the required data. {table_access_reason}"
        error_answer = {
            "message": error_msg,
            "sql_query": sql,
            "row_count": 0,
        }
        ConversationManager.append_turn(conversation_id, user_query, error_answer, title_hint=user_query, user_id=user_id, is_first_message=is_first_message, message_position=message_position)
        return jsonify({
            "success": False,
            "conversation_id": conversation_id,
            "rewritten_query": consolidated,
            "sql_query": sql,
            "error": f"Table access denied: {table_access_reason}",
            "message": error_msg,
        }), 403
    
    # ----- Validate company_fk: reject queries with hardcoded wrong company_fk ----- #
    user_company_fk = _company_filter_ids(ctx)
    if user_company_fk and not ctx.get("is_admin"):
        has_wrong_fk, fk_reason = sql_guard.detect_wrong_company_fk(sql, user_company_fk)
        if has_wrong_fk:
            logger.warning(f"❌ Query has wrong company_fk: {fk_reason} | {sql}")
            # Treat as a correction trigger - will force regeneration
            correction_log.append({
                "attempt": 0,
                "error": fk_reason,
                "sql": sql,
                "reason": "hardcoded_wrong_company_fk"
            })
            # Generate corrected SQL
            try:
                corrected = svc.correct_sql(consolidated, sql, fk_reason, history)
                corrected = sql_guard.sanitize(corrected)
                ok, why = sql_guard.validate(corrected)
                if ok:
                    sql = corrected
                    logger.info(f"Regenerated SQL after company_fk correction: {sql}")
                else:
                    logger.warning(f"Corrected SQL is invalid: {why}")
            except Exception as exc:
                logger.warning(f"Could not regenerate SQL: {exc}")
    
    sql = sql_guard.enforce_limit(sql)
    
    # ----- MANDATORY: Enforce company_fk filtering ----- #
    # Use the full allowed id set (parent company + child branches) from the SOURCE DB.
    company_fk = _company_filter_ids(ctx)
    if company_fk and not ctx.get("is_admin"):
        sql = sql_guard.enforce_company_fk(sql, company_fk)
        logger.info(f"[✓] Enforced company_fk in {company_fk} on query (user: {username})")

    # ----- Execute with self-correction loop ----- #
    rows, columns, row_count, run_error = _execute(svc, sql)
    attempts = 0
    while run_error and attempts < MAX_CORRECTION_ATTEMPTS:
        attempts += 1
        logger.warning(f"🔁 Self-correction attempt {attempts}: {run_error}")
        correction_log.append({"attempt": attempts, "error": run_error, "sql": sql})
        try:
            fixed = svc.correct_sql(consolidated, sql, run_error, history)
            fixed = sql_guard.sanitize(fixed)
            ok, why = sql_guard.validate(fixed)
            if not ok:
                run_error = f"Correction blocked: {why}"
                break
            
            # Check if corrected query still has wrong company_fk
            if user_company_fk and not ctx.get("is_admin"):
                has_wrong_fk, fk_reason = sql_guard.detect_wrong_company_fk(fixed, user_company_fk)
                if has_wrong_fk:
                    logger.warning(f"Corrected SQL still has wrong company_fk: {fk_reason}")
                    run_error = fk_reason
                    continue  # Trigger another correction attempt
            
            sql = sql_guard.enforce_limit(fixed)
            # Re-enforce company_fk on the corrected query
            if company_fk and not ctx.get("is_admin"):
                sql = sql_guard.enforce_company_fk(sql, company_fk)
            rows, columns, row_count, run_error = _execute(svc, sql)
        except Exception as exc:  # noqa: BLE001
            run_error = str(exc)
            break

    duration_ms = int((time.time() - started) * 1000)

    # ----- Analysis: chart spec, trend, insights ----- #
    analysis = {"visualization": {"type": "table", "columns": columns}, "trend": None, "insights": []}
    if run_error is None and rows:
        try:
            analysis = analyze(columns, rows, user_query)
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"Analysis failed: {exc}")

    default_message = (
        f"Returned {row_count} row(s)." if run_error is None
        else f"Generated SQL but execution failed: {run_error}"
    )

    # Conversational answer following the shared response guide.
    from ..responder import compose_answer
    message = compose_answer(
        llm, user_query, sql, columns, rows, row_count, run_error
    ) or default_message
    response_usage = _usage_snapshot(llm)

    token_usage = {
        "rewrite": rewrite_usage,
        "routing": routing_usage,
        "sql_generation": sql_usage,
        "response": response_usage,
        "total": _merge_usage(rewrite_usage, routing_usage, sql_usage, response_usage),
    }

    llm_settings = get_llm_settings()

    answer = {
        "message": message,
        "sql_query": sql,
        "row_count": row_count,
        "columns": columns,
        "data": rows,
        "visualization": analysis.get("visualization"),
        "trend": analysis.get("trend"),
        "insights": analysis.get("insights", []),
        "corrections": correction_log,
        "rewritten_query": consolidated,
        "rewrite_info": info,
        "error": run_error,
        "success": run_error is None,
        "llm_provider": llm_settings.get("provider"),
        "llm_model": llm_settings.get("model"),
    }
    ConversationManager.append_turn(conversation_id, user_query, answer, title_hint=user_query, user_id=user_id, is_first_message=is_first_message, message_position=message_position)

    total_usage = token_usage["total"]
    _audit(conversation_id, user_query, consolidated, sql, row_count,
           success=(run_error is None), error=run_error, duration_ms=duration_ms,
            provider=llm_settings.get("provider"), model=llm_settings.get("model"),
            response_text=message,
            context_cache=getattr(svc, "last_context_cache", {}),
            token_usage=token_usage,
            token_input=total_usage.get("input_tokens", 0),
            token_output=total_usage.get("output_tokens", 0),
            cache_creation_tokens=total_usage.get("cache_creation_input_tokens", 0),
            cache_read_tokens=total_usage.get("cache_read_input_tokens", 0),
            is_api=is_api, user_id=user_id)

    return jsonify({
        "success": run_error is None,
        "conversation_id": conversation_id,
        "query": user_query,
        "rewritten_query": consolidated,
        "rewrite_info": info,
        "route": "database",
        "route_reason": route_decision.get("reason"),
        "sql_query": sql,
        "columns": columns,
        "data": rows,
        "row_count": row_count,
        "message": message,
        "error": run_error,
        "visualization": analysis.get("visualization"),
        "trend": analysis.get("trend"),
        "insights": analysis.get("insights", []),
        "corrections": correction_log,
        "llm_provider": llm_settings.get("provider"),
        "llm_model": llm_settings.get("model"),
        "duration_ms": duration_ms,
        "token_usage": token_usage,
        "context_cache": getattr(svc, "last_context_cache", {}),
        "is_first_message": is_first_message,
        "message_position": message_position,
    }), 200


@chat_bp.route("/refresh", methods=["POST"])
@require_auth
def refresh():
    """Re-run a previously generated SQL query without regenerating it."""
    data = request.get_json(silent=True) or {}
    sql = (data.get("sql_query") or "").strip()
    if not sql:
        return jsonify({"success": False, "error": "Missing 'sql_query'"}), 400

    svc = get_vanna_service()
    if not svc.ready:
        return jsonify({"success": False, "error": "Text-to-SQL engine not ready."}), 503

    sql = sql_guard.sanitize(sql)
    ctx = current_user_context()
    if ctx and not ctx.get("is_admin") and (ctx.get("company_id") or ctx.get("related_company_ids")):
        user_filter = UserQueryFilter(
            user_id=ctx.get("user_id"),
            company_id=ctx.get("company_id"),
            branch_id=ctx.get("branch_id"),
            is_admin=ctx.get("is_admin"),
            related_company_ids=ctx.get("related_company_ids") or [],
        )
        sql = user_filter.modify_sql_query(sql)
    safe, reason = sql_guard.validate(sql)
    if not safe:
        return jsonify({"success": False, "error": f"Blocked: {reason}"}), 400
    sql = sql_guard.enforce_limit(sql)
    
    # ----- MANDATORY: Enforce company_fk filtering ----- #
    # Use the full allowed id set (parent company + child branches) from the SOURCE DB.
    company_fk = _company_filter_ids(ctx)
    if company_fk and not ctx.get("is_admin"):
        sql = sql_guard.enforce_company_fk(sql, company_fk)

    rows, columns, row_count, run_error = _execute(svc, sql)
    analysis = {"visualization": {"type": "table", "columns": columns}, "trend": None, "insights": []}
    if run_error is None and rows:
        try:
            analysis = analyze(columns, rows, "refresh")
        except Exception:  # noqa: BLE001
            pass

    return jsonify({
        "success": run_error is None,
        "sql_query": sql,
        "columns": columns,
        "data": rows,
        "row_count": row_count,
        "error": run_error,
        "visualization": analysis.get("visualization"),
        "trend": analysis.get("trend"),
        "insights": analysis.get("insights", []),
    }), 200


@chat_bp.route("/run-sql", methods=["POST"])
@require_auth
def run_sql():
    """Execute a (possibly edited) SQL statement directly."""
    data = request.get_json(silent=True) or {}
    sql = (data.get("sql") or "").strip()
    if not sql:
        return jsonify({"success": False, "error": "Missing 'sql'"}), 400
    # Apply the same safety guard to user-edited SQL.
    sql = sql_guard.sanitize(sql)
    ctx = current_user_context()
    if ctx and not ctx.get("is_admin") and (ctx.get("company_id") or ctx.get("related_company_ids")):
        user_filter = UserQueryFilter(
            user_id=ctx.get("user_id"),
            company_id=ctx.get("company_id"),
            branch_id=ctx.get("branch_id"),
            is_admin=ctx.get("is_admin"),
            related_company_ids=ctx.get("related_company_ids") or [],
        )
        sql = user_filter.modify_sql_query(sql)
    safe, reason = sql_guard.validate(sql)
    if not safe:
        return jsonify({"success": False, "error": f"Blocked for safety: {reason}"}), 200
    sql = sql_guard.enforce_limit(sql)
    
    # ----- MANDATORY: Enforce company_fk filtering ----- #
    # Use the full allowed id set (parent company + child branches) from the SOURCE DB.
    company_fk = _company_filter_ids(ctx)
    if company_fk and not ctx.get("is_admin"):
        sql = sql_guard.enforce_company_fk(sql, company_fk)
    
    svc = get_vanna_service()
    if not svc.ready or not svc.status().get("connected_db"):
        return jsonify({"success": False, "error": "No source database connected."}), 503
    try:
        df = svc.run_sql(sql)
        return jsonify({
            "success": True,
            "columns": list(df.columns) if df is not None else [],
            "data": df.head(500).to_dict(orient="records") if df is not None else [],
            "row_count": int(len(df)) if df is not None else 0,
        }), 200
    except Exception as exc:  # noqa: BLE001
        return jsonify({"success": False, "error": str(exc)}), 500


@chat_bp.route("/public", methods=["POST"])
def public_query():
    """Public assistant for users who are NOT logged in.

    This route is intentionally unauthenticated and is restricted to the
    documentation/knowledge base. It:
      * answers ONLY from training documentation marked available to
        non-logged-in users (access="all"), via RAG retrieval;
      * NEVER generates or executes SQL and never touches the SOURCE database;
      * returns an articulated, grounded answer composed from the public docs.

    Body: { "query" | "message": str }
    """
    data = request.get_json(silent=True) or {}
    raw_query = (data.get("query") or data.get("message") or "").strip()
    # Guardrail: sanitize incoming text against prompt-injection.
    question = sql_guard.sanitize_user_text(raw_query)
    if not question:
        return jsonify({"success": False, "error": "Missing 'query' or 'message'"}), 400

    # Defense-in-depth: reject restricted keywords/commands in the prompt.
    blocked, keyword = sql_guard.contains_restricted(question)
    if blocked:
        return jsonify({
            "success": False,
            "error": f"Blocked: restricted keyword/command detected ({keyword}).",
            "message": "Your request contains a restricted keyword. Please rephrase.",
        }), 400

    svc = get_vanna_service()
    if not svc.ready:
        from ..bootstrap import reinitialize_vanna
        reinitialize_vanna()
        if not svc.ready:
            return jsonify({
                "success": False,
                "error": "Knowledge base is not ready. Please try again later.",
            }), 503

    started = time.time()
    llm = build_llm(get_llm_settings())

    # RAG over PUBLIC documentation ONLY. access_mode="guest" filters out any
    # entry marked authenticated-only, leaving documents available to everyone.
    message, kb_hits = _answer_knowledge_base(llm, svc, question, access_mode="guest")

    # Audit as a public (no-auth) request — no SQL is ever generated here.
    _audit(
        ConversationManager.new_id(), question, question, "", 0, success=True,
        duration_ms=int((time.time() - started) * 1000), is_api=_is_api_request(),
        user_id=None, username="public", role_name="public",
        context_cache={"knowledge_docs_used": kb_hits},
    )

    return jsonify({
        "success": True,
        "mode": "knowledge_base",
        "message": message,
        "knowledge_docs_used": kb_hits,
        "sql_query": None,
        "row_count": 0,
        "data": [],
    }), 200


def _get_audit_user_info(ctx):
    """Extract username and role_name from user context."""
    if not ctx:
        return None, None
    
    username = ctx.get("username")
    roles = ctx.get("roles") or []
    role_name = ", ".join(roles) if roles else None
    
    return username, role_name


def _audit(conversation_id, user_query, rewritten, sql, row_count, success=True,
           error=None, duration_ms=0, provider=None, model=None,
           response_text=None, context_cache=None, token_usage=None,
           token_input=0, token_output=0, cache_creation_tokens=0, cache_read_tokens=0,
           is_api=False, user_id=None, username=None, role_name=None):
    try:
        log = AuditLog(
            conversation_id=conversation_id, user_query=user_query,
            rewritten_query=rewritten, generated_sql=sql, row_count=row_count,
            success=success, error_message=error, duration_ms=duration_ms,
            llm_provider=provider, llm_model=model,
            is_api=is_api, user_id=user_id, username=username, role_name=role_name,
        )
        db.session.add(log)
        db.session.flush()
        detail = AuditLogDetail(
            audit_log_id=log.id,
            response_text=response_text,
            context_cache=json.dumps(context_cache or {}, default=str),
            token_usage=json.dumps(token_usage or {}, default=str),
            token_input=int(token_input or 0),
            token_output=int(token_output or 0),
            cache_creation_tokens=int(cache_creation_tokens or 0),
            cache_read_tokens=int(cache_read_tokens or 0),
        )
        db.session.add(detail)
        db.session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.debug(f"Audit log failed: {exc}")
        db.session.rollback()


@chat_bp.route("/translate-text", methods=["POST"])
@require_auth
def translate_text():
    """Translate text from one language to another using the configured LLM."""
    from ..translation import translate_to_english
    
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    source_language = (data.get("source_language") or "english").strip().lower()
    target_language = (data.get("target_language") or "english").strip().lower()
    
    if not text:
        return jsonify({"success": False, "error": "Missing 'text' field"}), 400
    
    if source_language == target_language:
        # No translation needed
        return jsonify({
            "success": True,
            "original_text": text,
            "translated_text": text,
            "source_language": source_language,
            "target_language": target_language,
        }), 200
    
    # Currently only supporting translation to English
    if target_language != "english":
        return jsonify({
            "success": False,
            "error": "Currently only translation to English is supported",
            "original_text": text,
        }), 400
    
    try:
        # Use the built-in translation module to translate to English
        translated_text = translate_to_english(text, source_language)
        return jsonify({
            "success": True,
            "original_text": text,
            "translated_text": translated_text,
            "source_language": source_language,
            "target_language": target_language,
        }), 200
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return jsonify({
            "success": False,
            "error": f"Translation failed: {str(e)}",
            "original_text": text,
        }), 500


@chat_bp.route("/synthesize-speech", methods=["POST"])
@require_auth
def synthesize_speech():
    """
    Convert text to speech for language testing.
    
    Supports multiple TTS providers:
    1. Browser Native TTS (Free, local, English only)
    2. Google Chirp TTS (Affordable, Google service)
    3. Google Cloud Text-to-Speech (Premium, best for African languages)
    4. Azure Text-to-Speech (Microsoft service, diverse voices)
    5. ElevenLabs Text-to-Speech (Premium, voice cloning)
    
    Request body:
    {
        "text": "Text to convert to speech",
        "language": "english|igbo|hausa|yoruba|pidgin",
        "gender": "MALE|FEMALE|NEUTRAL",
        "tts_provider": "browser|google-chirp|google-cloud|azure-tts|elevenlabs-tts|yarngpt-tts" (optional)
    }
    
    Returns:
    {
        "success": true/false,
        "audio": "data:audio/mp3;base64,...",  (if available)
        "provider": string,
        "use_browser_tts": true,  (if suggesting client-side TTS)
        "error": "if failed"
    }
    """
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    language = (data.get("language") or "english").strip().lower()
    gender = (data.get("gender") or "NEUTRAL").upper()
    tts_provider = (data.get("tts_provider") or "").strip().lower()
    
    if not text:
        return jsonify({"success": False, "error": "Missing 'text' field"}), 400
    
    # Language code mapping
    language_map = {
        'english': 'en-US',
        'igbo': 'ig-NG',
        'hausa': 'ha-NG',
        'yoruba': 'yo-NG',
        'pidgin': 'en-NG',
    }
    
    lang_code = language_map.get(language, 'en-US')
    
    # If no provider specified, try to get user's preference from settings
    if not tts_provider:
        from ..models import UserSettings
        user_audio_settings = {}
        try:
            ctx = current_user_context()
            if ctx.get('user_id'):
                user_settings = UserSettings.query.filter_by(user_id=ctx.get('user_id')).first()
                if user_settings:
                    user_audio_settings = user_settings.get_audio_settings() or {}
                    tts_provider = user_audio_settings.get('ttsProvider', '').strip()
        except:
            pass
        
        # Fall back to smart defaults if user hasn't configured a preference
        if not tts_provider:
            tts_provider = 'browser' if language == 'english' else 'google-cloud'
    
    # Try requested provider
    if tts_provider == 'browser':
        result = _tts_browser(text, language)
    elif tts_provider == 'google-chirp':
        result = _tts_google_chirp(text, language, lang_code, gender)
    elif tts_provider == 'google-cloud':
        result = _tts_google_cloud(text, language, lang_code, gender)
    elif tts_provider == 'azure-tts':
        result = _tts_azure(text, language, lang_code, gender)
    elif tts_provider == 'elevenlabs-tts':
        result = _tts_elevenlabs(text, language, gender)
    elif tts_provider == 'yarngpt-tts':
        result = _tts_yarngpt(text, language, gender)
    else:
        result = {"success": False, "error": f"Unknown provider: {tts_provider}"}
    
    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 503


def _tts_browser(text, language):
    """Browser native TTS (free, English only)."""
    if language != 'english':
        return {
            "success": False,
            "error": f"Browser TTS only supports English",
            "provider": "browser",
            "suggestion": "Use Google Chirp, Google Cloud, or Azure TTS for {language}"
        }
    
    return {
        "success": True,
        "use_browser_tts": True,
        "provider": "browser_native",
        "language": language,
        "message": "✓ Using browser native TTS (free, local)"
    }


def _tts_google_chirp(text, language, lang_code, gender):
    """Google Chirp TTS (affordable Google service)."""
    credentials_path = os.getenv('GOOGLE_CLOUD_TTS_CREDENTIALS_PATH')
    if credentials_path and os.path.exists(credentials_path):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
    
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        home_dir = os.path.expanduser('~')
        possible_paths = [
            os.path.join(home_dir, '.gcp', 'credentials.json'),
            os.path.join(home_dir, '.google', 'credentials.json'),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = path
                break
    
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        return {
            "success": False,
            "error": "Google Chirp TTS requires Google Cloud credentials",
            "provider": "google_chirp",
            "setup": "Set GOOGLE_CLOUD_TTS_CREDENTIALS_PATH in .env"
        }
    
    try:
        from google.cloud import texttospeech
        import base64
        
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        voice = texttospeech.VoiceSelectionParams(
            language_code=lang_code,
            ssml_gender=getattr(texttospeech.SsmlVoiceGender, gender, texttospeech.SsmlVoiceGender.NEUTRAL)
        )
        
        # Use Chirp codec for affordable option
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        audio_b64 = base64.b64encode(response.audio_content).decode('utf-8')
        logger.info(f"✓ Google Chirp TTS: {language}, {len(response.audio_content)} bytes")
        
        return {
            "success": True,
            "audio": f"data:audio/mp3;base64,{audio_b64}",
            "language": language,
            "provider": "google_chirp",
            "cost": "Affordable (~$1 per 1M characters)"
        }
    except Exception as e:
        logger.warning(f"Google Chirp TTS failed: {e}")
        return {
            "success": False,
            "error": f"Google Chirp TTS error: {str(e)}",
            "provider": "google_chirp"
        }


def _tts_google_cloud(text, language, lang_code, gender):
    """Google Cloud Text-to-Speech (premium, best quality)."""
    credentials_path = os.getenv('GOOGLE_CLOUD_TTS_CREDENTIALS_PATH')
    if credentials_path and os.path.exists(credentials_path):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
    
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        home_dir = os.path.expanduser('~')
        possible_paths = [
            os.path.join(home_dir, '.gcp', 'credentials.json'),
            os.path.join(home_dir, '.google', 'credentials.json'),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = path
                break
    
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        return {
            "success": False,
            "error": "Google Cloud TTS requires Google credentials",
            "provider": "google_cloud",
            "setup": "Set GOOGLE_CLOUD_TTS_CREDENTIALS_PATH in .env"
        }
    
    try:
        from google.cloud import texttospeech
        import base64
        
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        voice = texttospeech.VoiceSelectionParams(
            language_code=lang_code,
            ssml_gender=getattr(texttospeech.SsmlVoiceGender, gender, texttospeech.SsmlVoiceGender.NEUTRAL)
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        audio_b64 = base64.b64encode(response.audio_content).decode('utf-8')
        logger.info(f"✓ Google Cloud TTS: {language}, {len(response.audio_content)} bytes")
        
        return {
            "success": True,
            "audio": f"data:audio/mp3;base64,{audio_b64}",
            "language": language,
            "provider": "google_cloud",
            "cost": "Premium (~$15 per 1M characters)"
        }
    except Exception as e:
        logger.warning(f"Google Cloud TTS failed: {e}")
        return {
            "success": False,
            "error": f"Google Cloud TTS error: {str(e)}",
            "provider": "google_cloud"
        }


def _tts_azure(text, language, lang_code, gender):
    """Azure Text-to-Speech (Microsoft service)."""
    azure_key = os.getenv('AZURE_SPEECH_KEY', '').strip()
    azure_region = os.getenv('AZURE_SPEECH_REGION', '').strip()
    
    if not azure_key or not azure_region:
        return {
            "success": False,
            "error": "Azure TTS requires AZURE_SPEECH_KEY and AZURE_SPEECH_REGION",
            "provider": "azure_tts",
            "setup": "Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION in .env"
        }
    
    try:
        import azure.cognitiveservices.speech as speechsdk
        from io import BytesIO
        import base64
        
        speech_config = speechsdk.SpeechConfig(
            subscription=azure_key,
            region=azure_region
        )
        
        # Create audio stream
        audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=False)
        audio_stream = BytesIO()
        
        # Map gender to voice name
        voice_name = f"en-US-{gender.capitalize()}Neural"  # Example: en-US-MaleNeural
        speech_config.speech_synthesis_voice_name = voice_name
        
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config
        )
        
        result = synthesizer.speak_text_async(text).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            # Convert to base64
            audio_b64 = base64.b64encode(result.audio_data).decode('utf-8') if result.audio_data else ""
            logger.info(f"✓ Azure TTS: {language}, {len(result.audio_data or [])} bytes")
            
            return {
                "success": True,
                "audio": f"data:audio/wav;base64,{audio_b64}",
                "language": language,
                "provider": "azure_tts",
                "cost": "Free tier: 5M characters/month"
            }
        else:
            return {
                "success": False,
                "error": f"Azure synthesis failed: {result.error_details}",
                "provider": "azure_tts"
            }
    except ImportError:
        return {
            "success": False,
            "error": "Azure SDK not installed",
            "provider": "azure_tts",
            "setup": "pip install azure-cognitiveservices-speech"
        }
    except Exception as e:
        logger.warning(f"Azure TTS failed: {e}")
        return {
            "success": False,
            "error": f"Azure TTS error: {str(e)}",
            "provider": "azure_tts"
        }


def _tts_elevenlabs(text, language, gender):
    """ElevenLabs Text-to-Speech (premium voices)."""
    elevenlabs_key = os.getenv('ELEVENLABS_API_KEY', '').strip()
    
    if not elevenlabs_key:
        return {
            "success": False,
            "error": "ElevenLabs TTS requires ELEVENLABS_API_KEY",
            "provider": "elevenlabs_tts",
            "setup": "Set ELEVENLABS_API_KEY in .env"
        }
    
    try:
        from elevenlabs import ElevenLabs, Voice, VoiceSettings
        import base64
        
        client = ElevenLabs(api_key=elevenlabs_key)
        
        # Get voice based on gender
        # Note: get_all() returns GetVoicesResponse object, need to access .voices attribute
        voices_response = client.voices.get_all()
        voices = voices_response.voices if hasattr(voices_response, 'voices') else []
        
        if not voices:
            logger.warning("No voices available from ElevenLabs")
            return {
                "success": False,
                "error": "No voices available from ElevenLabs",
                "provider": "elevenlabs_tts",
                "suggestion": "Check API key has 'voices_read' permission"
            }
        
        # Find voice by gender preference
        if gender == 'MALE':
            voice = next((v for v in voices if 'male' in v.name.lower()), voices[0] if voices else None)
        else:
            voice = next((v for v in voices if 'female' in v.name.lower()), voices[0] if voices else None)
        
        if not voice:
            logger.error("No voice found for gender: " + gender)
            return {
                "success": False,
                "error": "No voices available for selected gender",
                "provider": "elevenlabs_tts",
                "suggestion": "Check API key has 'voices_read' permission"
            }
        
        logger.debug(f"Selected voice: {voice.name} (ID: {voice.voice_id})")
        
        # Convert text to speech
        # Note: Using eleven_flash_v2_5 (latest, fastest model)
        # Deprecated models: eleven_monolingual_v1, eleven_multilingual_v1
        audio = client.text_to_speech.convert(
            text=text,
            voice_id=voice.voice_id,
            model_id="eleven_flash_v2_5"
        )
        
        # audio is a generator/iterator, collect bytes
        audio_bytes = b"".join(audio)
        
        if not audio_bytes:
            logger.error("No audio data received from ElevenLabs")
            return {
                "success": False,
                "error": "ElevenLabs returned empty audio",
                "provider": "elevenlabs_tts"
            }
        
        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        logger.info(f"✅ ElevenLabs TTS: {language}, Voice: {voice.name}, {len(audio_bytes)} bytes")
        
        return {
            "success": True,
            "audio": f"data:audio/mpeg;base64,{audio_b64}",
            "language": language,
            "provider": "elevenlabs_tts",
            "voice": voice.name,
            "cost": "Premium: $5-99/month"
        }
    except ImportError as e:
        logger.error(f"❌ ElevenLabs import error: {str(e)}")
        return {
            "success": False,
            "error": f"ElevenLabs SDK import failed: {str(e)[:60]}",
            "provider": "elevenlabs_tts",
            "setup": "pip install elevenlabs"
        }
    except TypeError as e:
        # Handle 'GetVoicesResponse' object is not subscriptable error
        error_str = str(e)
        logger.error(f"❌ ElevenLabs TypeError (likely API response format issue): {error_str}")
        return {
            "success": False,
            "error": f"ElevenLabs API response format error. Ensure API key has 'voices_read' permission.",
            "provider": "elevenlabs_tts",
            "setup": "Visit https://elevenlabs.io/app/settings/api-keys and enable 'voices_read' permission",
            "details": error_str[:60]
        }
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ ElevenLabs TTS failed: {error_str[:200]}")
        logger.error(f"Full exception: {error_str}")  # Log full error for debugging
        
        # Check for specific HTTP status codes
        if '503' in error_str or 'Service Unavailable' in error_str:
            return {
                "success": False,
                "error": "ElevenLabs API temporarily unavailable (503 Service Unavailable)",
                "provider": "elevenlabs_tts",
                "details": "The ElevenLabs service is temporarily unavailable. This could be due to:\n• API service maintenance\n• Rate limiting\n• API key permission issues\n• Regional availability",
                "troubleshoot": "1. Check ElevenLabs status: https://status.elevenlabs.io\n2. Verify API key permissions at https://elevenlabs.io/app/settings/api-keys\n3. Ensure these permissions are enabled: voices_read, text_to_speech_create\n4. Try again in a few moments"
            }
        elif '401' in error_str or 'unauthorized' in error_str.lower():
            return {
                "success": False,
                "error": "ElevenLabs API key is invalid or expired (401 Unauthorized)",
                "provider": "elevenlabs_tts",
                "setup": "Check ELEVENLABS_API_KEY in .env - verify it's correct and hasn't expired"
            }
        elif '403' in error_str or 'forbidden' in error_str.lower():
            return {
                "success": False,
                "error": "ElevenLabs API key missing required permissions (403 Forbidden)",
                "provider": "elevenlabs_tts",
                "setup": "Visit https://elevenlabs.io/app/settings/api-keys\nEnable these permissions:\n✓ voices_read\n✓ text_to_speech_create\n✓ audio_to_text_create"
            }
        elif 'missing_permissions' in error_str or 'voices_read' in error_str:
            return {
                "success": False,
                "error": "ElevenLabs API key missing 'voices_read' permission.",
                "provider": "elevenlabs_tts",
                "setup": "Visit https://elevenlabs.io/app/settings/api-keys and verify these permissions are enabled:\n✓ voices_read\n✓ text_to_speech_create"
            }
        elif 'subscriptable' in error_str or 'GetVoicesResponse' in error_str:
            return {
                "success": False,
                "error": "ElevenLabs response parsing error. Likely due to missing 'voices_read' permission.",
                "provider": "elevenlabs_tts",
                "setup": "Verify your API key has these permissions:\n✓ voices_read\n✓ text_to_speech_create\n✓ audio_to_text_create"
            }
        else:
            return {
                "success": False,
                "error": f"ElevenLabs TTS error: {error_str[:80]}",
                "provider": "elevenlabs_tts",
                "debug": error_str[:120]
            }


def _tts_yarngpt(text, language, gender):
    """
    YarnGPT Text-to-Speech (multilingual premium voices).
    
    Fallback chain:
    1. YarnGPT API
    2. Google Cloud TTS (if configured)
    3. ElevenLabs TTS (if configured)
    4. Browser TTS (as last resort for English)
    """
    yarngpt_key = os.getenv('YARNGPT_API_KEY', '').strip()
    
    # Try YarnGPT first
    if yarngpt_key:
        try:
            import requests
            
            # YarnGPT API endpoint
            api_url = "https://api.yarngpt.app/v1/tts"
            
            headers = {
                "Authorization": f"Bearer {yarngpt_key}",
                "Content-Type": "application/json"
            }
            
            # Prepare request payload
            payload = {
                "text": text,
                "language": language,
                "voice_type": "premium",
                "gender": gender if gender in ['MALE', 'FEMALE'] else 'NEUTRAL'
            }
            
            # Call YarnGPT API with timeout
            response = requests.post(api_url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Get audio data from response
                audio_data = response.content
                if audio_data:
                    import base64
                    audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                    logger.info(f"✓ YarnGPT TTS successful: {language}, {len(audio_data)} bytes")
                    return {
                        "success": True,
                        "audio": f"data:audio/mpeg;base64,{audio_b64}",
                        "language": language,
                        "provider": "yarngpt_tts",
                        "cost": "Premium: Pay-as-you-go"
                    }
            else:
                logger.warning(f"YarnGPT: HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.warning("YarnGPT: Request timeout (>10s)")
        except requests.exceptions.ConnectionError:
            logger.warning("YarnGPT: Connection error - endpoint unreachable")
        except Exception as e:
            logger.warning(f"YarnGPT TTS error: {str(e)[:100]}")
    
    # Language code mapping for fallback services
    language_map = {
        'english': 'en-US',
        'igbo': 'ig-NG',
        'hausa': 'ha-NG',
        'yoruba': 'yo-NG',
        'pidgin': 'en-NG',
    }
    lang_code = language_map.get(language, 'en-US')
    
    # Try Google Cloud TTS as first fallback
    logger.info("🔄 YarnGPT unavailable, trying Google Cloud TTS...")
    google_result = _tts_google_cloud(text, language, lang_code, gender)
    if google_result.get('success'):
        return google_result
    
    # Try ElevenLabs TTS as second fallback
    logger.info("🔄 Google Cloud unavailable, trying ElevenLabs TTS...")
    elevenlabs_result = _tts_elevenlabs(text, language, gender)
    if elevenlabs_result.get('success'):
        return elevenlabs_result
    
    # Final fallback: Browser TTS for English only
    if language == 'english':
        logger.info("🔄 Premium services unavailable, using browser TTS...")
        return _tts_browser(text, language)
    
    # No TTS service available
    logger.error(f"All TTS services failed for {language}")
    return {
        "success": False,
        "error": "No TTS service available. Check configuration.",
        "provider": "yarngpt_tts_with_fallback",
        "note": "YarnGPT endpoint unreachable, Google Cloud and ElevenLabs not configured or failed"
    }


