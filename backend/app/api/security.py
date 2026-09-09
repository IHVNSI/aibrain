"""Security API: restricted SQL commands + custom restricted keywords (admin-only)."""
import logging

from flask import Blueprint, request, jsonify

from ..extensions import db
from ..models import RestrictedSQLCommand, Setting
from ..auth import require_auth, current_user_context

logger = logging.getLogger(__name__)
security_bp = Blueprint("security", __name__, url_prefix="/api/security")


def _admin_only():
    return bool(current_user_context().get("is_admin"))


@security_bp.route("/commands", methods=["GET"])
@require_auth
def list_commands():
    rows = RestrictedSQLCommand.query.order_by(RestrictedSQLCommand.command.asc()).all()
    return jsonify({"success": True, "commands": [r.to_dict() for r in rows]}), 200


@security_bp.route("/commands", methods=["POST"])
@require_auth
def add_command():
    if not _admin_only():
        return jsonify({"success": False, "error": "Admin access required"}), 403
    data = request.get_json(silent=True) or {}
    cmd = (data.get("command") or "").strip().upper()
    if not cmd:
        return jsonify({"success": False, "error": "Missing 'command'"}), 400
    existing = RestrictedSQLCommand.query.filter_by(command=cmd).first()
    if existing:
        existing.is_blocked = bool(data.get("is_blocked", True))
        existing.description = data.get("description", existing.description)
    else:
        db.session.add(RestrictedSQLCommand(
            command=cmd, is_blocked=bool(data.get("is_blocked", True)),
            description=data.get("description", ""),
        ))
    db.session.commit()
    return jsonify({"success": True}), 200


@security_bp.route("/commands/<int:cmd_id>", methods=["PATCH"])
@require_auth
def toggle_command(cmd_id):
    if not _admin_only():
        return jsonify({"success": False, "error": "Admin access required"}), 403
    row = RestrictedSQLCommand.query.get(cmd_id)
    if not row:
        return jsonify({"success": False, "error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    if "is_blocked" in data:
        row.is_blocked = bool(data["is_blocked"])
    if "description" in data:
        row.description = data["description"]
    db.session.commit()
    return jsonify({"success": True, "command": row.to_dict()}), 200


@security_bp.route("/commands/<int:cmd_id>", methods=["DELETE"])
@require_auth
def delete_command(cmd_id):
    if not _admin_only():
        return jsonify({"success": False, "error": "Admin access required"}), 403
    row = RestrictedSQLCommand.query.get(cmd_id)
    if not row:
        return jsonify({"success": False, "error": "Not found"}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"success": True}), 200


@security_bp.route("/keywords", methods=["GET"])
@require_auth
def get_keywords():
    return jsonify({"success": True, "keywords": Setting.get("restricted_keywords") or []}), 200


@security_bp.route("/keywords", methods=["POST"])
@require_auth
def set_keywords():
    if not _admin_only():
        return jsonify({"success": False, "error": "Admin access required"}), 403
    data = request.get_json(silent=True) or {}
    kws = data.get("keywords")
    if not isinstance(kws, list):
        return jsonify({"success": False, "error": "'keywords' must be a list"}), 400
    cleaned = sorted({str(k).strip() for k in kws if str(k).strip()})
    Setting.set("restricted_keywords", cleaned)
    return jsonify({"success": True, "keywords": cleaned}), 200
