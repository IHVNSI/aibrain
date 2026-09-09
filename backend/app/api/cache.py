"""Cache / metrics API: audit-log-derived caching & usage metrics."""
import logging
from datetime import datetime, timedelta
import json

from flask import Blueprint, request, jsonify
from sqlalchemy import func

from ..extensions import db
from ..models import AuditLog, AuditLogDetail
from ..llm import get_llm_settings
from ..auth import require_auth, current_user_context

logger = logging.getLogger(__name__)
cache_bp = Blueprint("cache", __name__, url_prefix="/api/cache")


@cache_bp.route("/metrics", methods=["GET"])
@require_auth
def metrics():
    """High-level query/caching metrics derived from the audit log.
    
    Note: Restricted to admins to prevent exposure of system-wide performance data.
    """
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    hours = request.args.get("hours", 24, type=int)
    since = datetime.utcnow() - timedelta(hours=max(1, hours))
    logs = AuditLog.query.filter(AuditLog.created_at >= since).all()

    total = len(logs)
    success = sum(1 for l in logs if l.success)
    failed = total - success
    avg_ms = int(sum(l.duration_ms or 0 for l in logs) / total) if total else 0
    by_provider = {}
    for l in logs:
        key = f"{l.llm_provider or 'unknown'}/{l.llm_model or '?'}"
        by_provider[key] = by_provider.get(key, 0) + 1

    log_ids = [l.id for l in logs]
    details = AuditLogDetail.query.filter(AuditLogDetail.audit_log_id.in_(log_ids)).all() if log_ids else []
    token_input = sum(d.token_input or 0 for d in details)
    token_output = sum(d.token_output or 0 for d in details)
    cache_creation_tokens = sum(d.cache_creation_tokens or 0 for d in details)
    cache_read_tokens = sum(d.cache_read_tokens or 0 for d in details)
    token_saved = cache_read_tokens

    return jsonify({
        "success": True,
        "metrics": {
            "period_hours": hours,
            "total_queries": total,
            "successful": success,
            "failed": failed,
            "success_rate": round(success / total * 100, 1) if total else 0.0,
            "avg_duration_ms": avg_ms,
            "by_provider": by_provider,
            "active_llm": get_llm_settings().get("provider"),
            "tokens": {
                "input": token_input,
                "output": token_output,
                "cache_creation": cache_creation_tokens,
                "cache_read": cache_read_tokens,
                "saved_by_cache": token_saved,
            },
        },
    }), 200


@cache_bp.route("/recent", methods=["GET"])
@require_auth
def recent():
    """Recent query audit entries (authenticated users can see their own audit logs).
    
    Note: Admins see all logs; regular users see only their own.
    """
    ctx = current_user_context() or {}
    user_id = ctx.get("user_id")
    is_admin = ctx.get("is_admin")
    
    limit = min(request.args.get("limit", 50, type=int), 200)
    
    # Filter by user if not admin
    if is_admin:
        logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    else:
        logs = AuditLog.query.filter_by(user_id=user_id).order_by(AuditLog.created_at.desc()).limit(limit).all()
    ids = [l.id for l in logs]
    details = AuditLogDetail.query.filter(AuditLogDetail.audit_log_id.in_(ids)).all() if ids else []
    detail_map = {d.audit_log_id: d for d in details}
    out = []
    for l in logs:
        base = l.to_dict()
        d = detail_map.get(l.id)
        if d:
            base.update({
                "token_input": d.token_input or 0,
                "token_output": d.token_output or 0,
                "cache_creation_tokens": d.cache_creation_tokens or 0,
                "cache_read_tokens": d.cache_read_tokens or 0,
            })
        out.append(base)
    return jsonify({"success": True, "items": out}), 200


@cache_bp.route("/audit-logs", methods=["GET"])
@require_auth
def audit_logs():
    """
    Audit logs enriched with token/cache and response summary.
    
    Note: Admins see all logs; regular users see only their own.
    
    Query params:
    - limit: Max results per page (default 50, max 200)
    - offset: Pagination offset (default 0)
    - is_api: Filter by API requests (true/false)
    - conversation_id: Filter by conversation ID
    - success: Filter by success status (true/false)
    - search: Search in user_query and rewritten_query
    - sort: Sort field (created_at, duration_ms, etc.) with - prefix for desc
    """
    ctx = current_user_context() or {}
    user_id = ctx.get("user_id")
    is_admin = ctx.get("is_admin")
    
    limit = min(request.args.get("limit", 50, type=int), 200)
    offset = request.args.get("offset", 0, type=int)
    is_api_filter = request.args.get("is_api")
    conversation_filter = request.args.get("conversation_id", "").strip()
    success_filter = request.args.get("success")
    search_term = request.args.get("search", "").strip()
    sort_by = request.args.get("sort", "-created_at")  # Default: newest first
    
    # Build query
    query = AuditLog.query
    
    # Apply user filter if not admin
    if not is_admin:
        query = query.filter_by(user_id=user_id)
    
    # Apply filters
    if is_api_filter is not None:
        is_api_val = is_api_filter.lower() in ("true", "1", "yes")
        query = query.filter_by(is_api=is_api_val)
    
    if conversation_filter:
        query = query.filter_by(conversation_id=conversation_filter)
    
    if success_filter is not None:
        success_val = success_filter.lower() in ("true", "1", "yes")
        query = query.filter_by(success=success_val)
    
    if search_term:
        search_pattern = f"%{search_term}%"
        query = query.filter(
            db.or_(
                AuditLog.user_query.ilike(search_pattern),
                AuditLog.rewritten_query.ilike(search_pattern)
            )
        )
    
    # Get total count before pagination
    total_count = query.count()
    
    # Apply sorting
    if sort_by.startswith("-"):
        sort_field = sort_by[1:]
        if hasattr(AuditLog, sort_field):
            query = query.order_by(getattr(AuditLog, sort_field).desc())
    else:
        if hasattr(AuditLog, sort_by):
            query = query.order_by(getattr(AuditLog, sort_by).asc())
    
    # Apply pagination
    logs = query.offset(offset).limit(limit).all()
    ids = [l.id for l in logs]
    details = AuditLogDetail.query.filter(AuditLogDetail.audit_log_id.in_(ids)).all() if ids else []
    detail_map = {d.audit_log_id: d for d in details}

    items = []
    for l in logs:
        base = l.to_dict()
        d = detail_map.get(l.id)
        if d:
            base["token_input"] = d.token_input or 0
            base["token_output"] = d.token_output or 0
            base["cache_creation_tokens"] = d.cache_creation_tokens or 0
            base["cache_read_tokens"] = d.cache_read_tokens or 0
            base["response_preview"] = (d.response_text or "")[:240]
        items.append(base)

    return jsonify({
        "success": True,
        "items": items,
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "hasMore": offset + limit < total_count
    }), 200


@cache_bp.route("/audit-logs/<int:audit_id>", methods=["GET"])
@require_auth
def audit_log_detail(audit_id: int):
    """Full audit-log detail payload for modal inspection.
    
    Note: Users can only view their own audit logs; admins can view all.
    """
    ctx = current_user_context() or {}
    user_id = ctx.get("user_id")
    is_admin = ctx.get("is_admin")
    
    log = AuditLog.query.get(audit_id)
    if not log:
        return jsonify({"success": False, "error": "Audit log not found."}), 404
    
    # Check access
    if not is_admin and log.user_id != user_id:
        return jsonify({"success": False, "error": "Access denied"}), 403
    
    detail = AuditLogDetail.query.filter_by(audit_log_id=log.id).first()
    payload = log.to_dict()
    payload["detail"] = detail.to_dict() if detail else {
        "response_text": "",
        "context_cache": {},
        "token_usage": {},
        "token_input": 0,
        "token_output": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
    }
    return jsonify({"success": True, "item": payload}), 200


@cache_bp.route("/audit-logs/bulk-delete", methods=["POST"])
@require_auth
def bulk_delete_audit_logs():
    """Bulk delete audit logs by ID list.
    
    Note: Only admins can delete audit logs.
    
    Request:
        {
            "audit_log_ids": [1, 2, 3, ...]  // List of audit log IDs to delete
        }
    
    Response:
        {
            "success": true,
            "deleted_count": 3,
            "message": "Deleted 3 audit log records"
        }
    """
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    
    data = request.get_json(silent=True) or {}
    audit_log_ids = data.get("audit_log_ids", [])
    
    if not audit_log_ids:
        return jsonify({"success": False, "error": "audit_log_ids list is required"}), 400
    
    if not isinstance(audit_log_ids, list):
        return jsonify({"success": False, "error": "audit_log_ids must be a list"}), 400
    
    if len(audit_log_ids) == 0:
        return jsonify({"success": True, "deleted_count": 0, "message": "No audit logs to delete"}), 200
    
    if len(audit_log_ids) > 1000:
        return jsonify({
            "success": False,
            "error": f"Cannot delete more than 1000 records at once (requested {len(audit_log_ids)})"
        }), 400
    
    try:
        # Convert IDs to integers and filter
        log_ids = []
        for id_val in audit_log_ids:
            try:
                log_ids.append(int(id_val))
            except (TypeError, ValueError):
                pass
        
        if not log_ids:
            return jsonify({"success": False, "error": "No valid audit log IDs provided"}), 400
        
        # Delete related audit log details first
        detail_count = AuditLogDetail.query.filter(
            AuditLogDetail.audit_log_id.in_(log_ids)
        ).delete(synchronize_session=False)
        
        # Delete audit logs
        deleted_count = AuditLog.query.filter(
            AuditLog.id.in_(log_ids)
        ).delete(synchronize_session=False)
        
        db.session.commit()
        
        logger.info(f"✓ Bulk deleted {deleted_count} audit logs (and {detail_count} detail records)")
        
        return jsonify({
            "success": True,
            "deleted_count": deleted_count,
            "detail_records_deleted": detail_count,
            "message": f"Deleted {deleted_count} audit log records"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during bulk delete: {e}")
        return jsonify({
            "success": False,
            "error": f"Bulk delete failed: {str(e)}"
        }), 500


@cache_bp.route("/audit-logs/<int:audit_id>", methods=["DELETE"])
@require_auth
def delete_audit_log(audit_id: int):
    """Delete a single audit log record.
    
    Note: Only admins can delete audit logs.
    """
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({"success": False, "error": "Admin access required"}), 403
    
    log = AuditLog.query.get(audit_id)
    if not log:
        return jsonify({"success": False, "error": "Audit log not found"}), 404
    
    try:
        # Delete related detail record first
        AuditLogDetail.query.filter_by(audit_log_id=audit_id).delete(synchronize_session=False)
        
        # Delete the audit log
        db.session.delete(log)
        db.session.commit()
        
        logger.info(f"✓ Deleted audit log {audit_id}")
        
        return jsonify({
            "success": True,
            "message": f"Deleted audit log {audit_id}"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting audit log {audit_id}: {e}")
        return jsonify({
            "success": False,
            "error": f"Delete failed: {str(e)}"
        }), 500
