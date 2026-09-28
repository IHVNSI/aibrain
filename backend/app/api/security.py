"""Security API: restricted SQL commands + custom restricted keywords (admin-only)."""
import logging

from flask import Blueprint, request, jsonify

from ..extensions import db
from ..models import RestrictedSQLCommand, Setting, AuthorizedContact
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


# ============================================================================
# AUTHORIZED CONTACTS ENDPOINTS (Email/Phone for remote SQL execution)
# ============================================================================

@security_bp.route("/authorized-contacts", methods=["GET"])
@require_auth
def list_authorized_contacts():
    """List all authorized contacts (emails/phones) for remote SQL execution."""
    try:
        # Optional filtering by active status
        active_only = request.args.get('active', 'true').lower() == 'true'
        
        query = AuthorizedContact.query
        if active_only:
            query = query.filter_by(is_active=True)
        
        contacts = query.order_by(AuthorizedContact.contact.asc()).all()
        
        return jsonify({
            "success": True,
            "contacts": [c.to_dict() for c in contacts],
            "count": len(contacts)
        }), 200
    
    except Exception as e:
        logger.error(f"Error listing authorized contacts: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@security_bp.route("/authorized-contacts", methods=["POST"])
@require_auth
def add_authorized_contact():
    """Add a new authorized email or phone number for remote SQL execution."""
    try:
        if not _admin_only():
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        data = request.get_json(silent=True) or {}
        
        # Validate required fields
        contact = (data.get("contact") or "").strip().lower()
        if not contact:
            return jsonify({"success": False, "error": "Missing 'contact' (email or phone)"}), 400
        
        # Detect contact type
        contact_type = data.get("contact_type", "email")  # email or phone
        if contact_type not in ['email', 'phone']:
            return jsonify({"success": False, "error": "'contact_type' must be 'email' or 'phone'"}), 400
        
        # Validate permission level
        permission_level = (data.get("permission_level") or "SELECT_ONLY").upper()
        valid_permissions = ['SELECT_ONLY', 'READ_WRITE', 'ADMIN']
        if permission_level not in valid_permissions:
            return jsonify({
                "success": False,
                "error": f"Invalid 'permission_level'. Must be one of: {', '.join(valid_permissions)}"
            }), 400
        
        # Check if already exists
        existing = AuthorizedContact.query.filter_by(contact=contact).first()
        if existing:
            return jsonify({
                "success": False,
                "error": f"Contact '{contact}' is already authorized"
            }), 409
        
        # Validate auto-reply mode if provided
        auto_reply_mode = data.get("auto_reply_mode", "draft")
        if auto_reply_mode:
            auto_reply_mode = auto_reply_mode.lower()
            valid_modes = ['draft', 'send']
            if auto_reply_mode not in valid_modes:
                return jsonify({
                    "success": False,
                    "error": f"Invalid 'auto_reply_mode'. Must be one of: {', '.join(valid_modes)}"
                }), 400
        
        # Create new authorized contact
        auth_contact = AuthorizedContact(
            contact=contact,
            contact_type=contact_type,
            permission_level=permission_level,
            description=data.get("description", ""),
            is_active=True,
            auto_reply_enabled=bool(data.get("auto_reply_enabled", False)),
            auto_reply_mode=auto_reply_mode,
            auto_reply_ai_instructions=data.get("auto_reply_ai_instructions", "").strip() or None,
            created_by=current_user_context().get("email", "unknown")
        )
        db.session.add(auth_contact)
        db.session.commit()
        
        logger.info(f"New authorized contact added: {contact} (Permission: {permission_level}, Auto-reply: {auth_contact.auto_reply_enabled})")
        
        return jsonify({
            "success": True,
            "message": f"Authorized contact '{contact}' added successfully",
            "contact": auth_contact.to_dict()
        }), 201
    
    except Exception as e:
        logger.error(f"Error adding authorized contact: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@security_bp.route("/authorized-contacts/<int:contact_id>", methods=["GET"])
@require_auth
def get_authorized_contact(contact_id):
    """Get details of a specific authorized contact."""
    try:
        contact = AuthorizedContact.query.get(contact_id)
        if not contact:
            return jsonify({"success": False, "error": "Contact not found"}), 404
        
        return jsonify({
            "success": True,
            "contact": contact.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting authorized contact: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@security_bp.route("/authorized-contacts/<int:contact_id>", methods=["PATCH"])
@require_auth
def update_authorized_contact(contact_id):
    """Update authorized contact permissions, description, or auto-reply settings."""
    try:
        if not _admin_only():
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        contact = AuthorizedContact.query.get(contact_id)
        if not contact:
            return jsonify({"success": False, "error": "Contact not found"}), 404
        
        data = request.get_json(silent=True) or {}
        
        # Update permission level if provided
        if "permission_level" in data:
            permission_level = (data.get("permission_level") or "").upper()
            valid_permissions = ['SELECT_ONLY', 'READ_WRITE', 'ADMIN']
            if permission_level not in valid_permissions:
                return jsonify({
                    "success": False,
                    "error": f"Invalid 'permission_level'. Must be one of: {', '.join(valid_permissions)}"
                }), 400
            contact.permission_level = permission_level
        
        # Update description if provided
        if "description" in data:
            contact.description = data.get("description", "")
        
        # Update active status if provided
        if "is_active" in data:
            contact.is_active = bool(data.get("is_active", True))
        
        # ============================================================
        # AUTO-REPLY SETTINGS
        # ============================================================
        if "auto_reply_enabled" in data:
            contact.auto_reply_enabled = bool(data.get("auto_reply_enabled", False))
        
        if "auto_reply_mode" in data:
            mode = (data.get("auto_reply_mode") or "draft").lower()
            valid_modes = ['draft', 'send']
            if mode not in valid_modes:
                return jsonify({
                    "success": False,
                    "error": f"Invalid 'auto_reply_mode'. Must be one of: {', '.join(valid_modes)}"
                }), 400
            contact.auto_reply_mode = mode
        
        if "auto_reply_ai_instructions" in data:
            contact.auto_reply_ai_instructions = data.get("auto_reply_ai_instructions", "").strip() or None
        
        db.session.commit()
        
        logger.info(f"Authorized contact updated: {contact.contact} (Permission: {contact.permission_level}, Auto-reply: {contact.auto_reply_enabled})")
        
        return jsonify({
            "success": True,
            "message": "Contact updated successfully",
            "contact": contact.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Error updating authorized contact: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@security_bp.route("/authorized-contacts/<int:contact_id>", methods=["DELETE"])
@require_auth
def delete_authorized_contact(contact_id):
    """Remove an authorized contact."""
    try:
        if not _admin_only():
            return jsonify({"success": False, "error": "Admin access required"}), 403
        
        contact = AuthorizedContact.query.get(contact_id)
        if not contact:
            return jsonify({"success": False, "error": "Contact not found"}), 404
        
        contact_identifier = contact.contact
        db.session.delete(contact)
        db.session.commit()
        
        logger.info(f"Authorized contact removed: {contact_identifier}")
        
        return jsonify({
            "success": True,
            "message": f"Contact '{contact_identifier}' removed successfully"
        }), 200
    
    except Exception as e:
        logger.error(f"Error deleting authorized contact: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@security_bp.route("/authorized-contacts/verify/<contact_string>", methods=["GET"])
@require_auth
def verify_contact_authorization(contact_string):
    """Verify if a contact is authorized and get their permission level."""
    try:
        # Optional: specify required permission level
        required_permission = request.args.get('require', 'SELECT_ONLY')
        
        permission_level = AuthorizedContact.get_permission_level(contact_string)
        is_authorized = AuthorizedContact.is_authorized(contact_string, required_permission)
        
        return jsonify({
            "success": True,
            "contact": contact_string,
            "is_authorized": is_authorized,
            "permission_level": permission_level,
            "required_permission": required_permission
        }), 200
    
    except Exception as e:
        logger.error(f"Error verifying contact authorization: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

