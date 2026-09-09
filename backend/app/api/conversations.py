"""Conversations API: SQLite-backed multi-turn history (source of truth)."""
import logging

from flask import Blueprint, request, jsonify

from ..auth import require_auth, current_user_context
from ..conversation import ConversationManager
from ..models import Conversation, User
from ..extensions import db

logger = logging.getLogger(__name__)
conversations_bp = Blueprint("conversations", __name__, url_prefix="/api/conversations")


def _get_user_company_ids(user_id: int) -> set:
    """Get all company IDs that a user has access to (for multi-tenant filtering)."""
    user = User.query.get(user_id)
    if not user:
        return set()
    
    # Get user's primary company
    company_ids = {user.company_id} if user.company_id else set()
    
    # Get any related companies from the user context
    # (This would be populated from related_company_ids in auth)
    return company_ids


@conversations_bp.route("", methods=["GET"])
@conversations_bp.route("/", methods=["GET"])
@require_auth
def list_conversations():
    ctx = current_user_context() or {}
    user_id = ctx.get("user_id")
    is_admin = ctx.get("is_admin")
    company_id = ctx.get("company_id")
    related_company_ids = ctx.get("related_company_ids") or []
    
    # Build set of company IDs this user can access
    user_companies = set(related_company_ids) if related_company_ids else set()
    if company_id:
        user_companies.add(company_id)
    
    # Admin can see all conversations; others see only:
    # 1. Their own conversations
    # 2. Shared conversations from their company
    if is_admin:
        convs = Conversation.query.order_by(Conversation.updated_at.desc()).all()
    elif user_companies:
        # Get user's own conversations + shared conversations from same company
        # Note: Shared conversations should ideally belong to users in the same company
        convs = Conversation.query.filter(
            (Conversation.user_id == user_id) | (Conversation.is_shared == True)
        ).order_by(Conversation.updated_at.desc()).all()
        # Filter shared conversations to only those from same company
        user_obj = User.query.get(user_id)
        user_company = user_obj.company_id if user_obj else None
        convs = [
            c for c in convs if c.user_id == user_id or (
                c.is_shared and User.query.get(c.user_id) and 
                User.query.get(c.user_id).company_id in user_companies
            )
        ]
    else:
        # User has no company assigned - only show their own conversations
        convs = Conversation.query.filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.updated_at.desc()).all()
    
    return jsonify({
        "success": True,
        "conversations": [c.to_dict(include_messages=False) for c in convs],
        "count": len(convs),
    }), 200


@conversations_bp.route("/<conversation_id>", methods=["GET"])
@require_auth
def get_conversation(conversation_id):
    ctx = current_user_context() or {}
    user_id = ctx.get("user_id")
    is_admin = ctx.get("is_admin")
    company_id = ctx.get("company_id")
    related_company_ids = ctx.get("related_company_ids") or []
    
    # Build set of company IDs this user can access
    user_companies = set(related_company_ids) if related_company_ids else set()
    if company_id:
        user_companies.add(company_id)
    
    conv = ConversationManager.get(conversation_id)
    if not conv:
        return jsonify({"success": False, "error": "Not found"}), 404
    
    # Check access: 
    # 1. Own conversation, or
    # 2. Admin, or
    # 3. Shared conversation from same company
    if is_admin:
        pass  # Admin can see everything
    elif conv.user_id == user_id:
        pass  # Owner can see their own
    elif conv.is_shared:
        # Check if shared conversation is from same company
        conv_owner = User.query.get(conv.user_id)
        if not conv_owner or conv_owner.company_id not in user_companies:
            return jsonify({"success": False, "error": "Access denied"}), 403
    else:
        return jsonify({"success": False, "error": "Access denied"}), 403
    
    return jsonify({"success": True, "conversation": conv.to_dict(include_messages=True)}), 200


@conversations_bp.route("/<conversation_id>", methods=["DELETE"])
@require_auth
def delete_conversation(conversation_id):
    ctx = current_user_context() or {}
    user_id = ctx.get("user_id")
    is_admin = ctx.get("is_admin")
    company_id = ctx.get("company_id")
    related_company_ids = ctx.get("related_company_ids") or []
    
    # Build set of company IDs this user can access
    user_companies = set(related_company_ids) if related_company_ids else set()
    if company_id:
        user_companies.add(company_id)
    
    conv = ConversationManager.get(conversation_id)
    if not conv:
        return jsonify({"success": False, "error": "Not found"}), 404
    
    # Only owner or admin can delete
    if not is_admin and conv.user_id != user_id:
        # Additional check: verify user is from same company
        conv_owner = User.query.get(conv.user_id)
        if not conv_owner or conv_owner.company_id not in user_companies:
            return jsonify({"success": False, "error": "Access denied"}), 403
    
    ok = ConversationManager.delete(conversation_id)
    return jsonify({"success": ok}), (200 if ok else 404)


@conversations_bp.route("/<conversation_id>/rename", methods=["POST"])
@require_auth
def rename_conversation(conversation_id):
    ctx = current_user_context() or {}
    user_id = ctx.get("user_id")
    is_admin = ctx.get("is_admin")
    company_id = ctx.get("company_id")
    related_company_ids = ctx.get("related_company_ids") or []
    
    # Build set of company IDs this user can access
    user_companies = set(related_company_ids) if related_company_ids else set()
    if company_id:
        user_companies.add(company_id)
    
    conv = ConversationManager.get(conversation_id)
    if not conv:
        return jsonify({"success": False, "error": "Not found"}), 404
    
    # Only owner or admin can rename
    if not is_admin and conv.user_id != user_id:
        # Additional check: verify user is from same company
        conv_owner = User.query.get(conv.user_id)
        if not conv_owner or conv_owner.company_id not in user_companies:
            return jsonify({"success": False, "error": "Access denied"}), 403
    
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"success": False, "error": "Missing 'title'"}), 400
    
    conv = ConversationManager.rename(conversation_id, title)
    if not conv:
        return jsonify({"success": False, "error": "Not found"}), 404
    return jsonify({"success": True, "conversation": conv.to_dict(include_messages=False)}), 200


@conversations_bp.route("/<conversation_id>/messages", methods=["PATCH"])
@require_auth
def update_messages(conversation_id):
    ctx = current_user_context() or {}
    user_id = ctx.get("user_id")
    
    conv = ConversationManager.get(conversation_id)
    if not conv:
        return jsonify({"success": False, "error": "Not found"}), 404
    
    # Only owner can update messages
    if not ctx.get("is_admin") and conv.user_id != user_id:
        return jsonify({"success": False, "error": "Access denied"}), 403
    
    data = request.get_json(silent=True) or {}
    messages = data.get("messages")
    if not isinstance(messages, list):
        return jsonify({"success": False, "error": "'messages' must be a list"}), 400
    
    conv = ConversationManager.update_messages(conversation_id, messages)
    if not conv:
        return jsonify({"success": False, "error": "Not found"}), 404
    return jsonify({"success": True, "conversation": conv.to_dict(include_messages=True)}), 200
