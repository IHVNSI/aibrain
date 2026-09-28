"""Email preview and sending - allows users to review email content before sending."""
import logging
from datetime import datetime
from typing import Tuple, Optional

from flask import Blueprint, request, jsonify
from jinja2 import Template, TemplateError

from ..extensions import db
from ..models import DraftEmail, SentEmail
from ..auth import require_auth, current_user_context
from .email_scheduling import send_email_smtp

logger = logging.getLogger(__name__)
email_send_bp = Blueprint("email_send", __name__, url_prefix="/api/email")


@email_send_bp.route("/preview", methods=["POST"])
@require_auth
def preview_email():
    """
    Preview an email before sending.
    
    Request body:
    {
        "to_address": "client@example.com",
        "subject": "Invoice #123 - Thank You",
        "body": "Dear Client,\n\nPlease find your invoice attached...",
        "cc": ["cc@example.com"],  # optional
        "bcc": ["bcc@example.com"],  # optional
        "attachments": [{"filename": "invoice.pdf", "data": "base64..."}],  # optional
        "template_variables": {"client_name": "John", "invoice_id": "123"}  # optional - for Jinja2
    }
    
    Returns preview with:
    - Rendered email content
    - Option to edit fields
    - Button to send or save as draft
    """
    try:
        ctx = current_user_context() or {}
        user_id = ctx.get("user_id")
        
        data = request.get_json() or {}
        to_address = (data.get("to_address") or "").strip()
        subject = (data.get("subject") or "").strip()
        body = (data.get("body") or "").strip()
        cc = data.get("cc") or []
        bcc = data.get("bcc") or []
        template_vars = data.get("template_variables") or {}
        
        # Validate required fields
        if not to_address:
            return jsonify({"success": False, "error": "Missing: to_address"}), 400
        if not subject:
            return jsonify({"success": False, "error": "Missing: subject"}), 400
        if not body:
            return jsonify({"success": False, "error": "Missing: body"}), 400
        
        # Try to render as Jinja2 template if variables provided
        rendered_body = body
        rendered_subject = subject
        
        if template_vars:
            try:
                template = Template(body)
                rendered_body = template.render(**template_vars)
                
                template = Template(subject)
                rendered_subject = template.render(**template_vars)
            except TemplateError as e:
                logger.warning(f"Template rendering error: {e}")
                # If template rendering fails, use as-is
                pass
        
        # Validate email addresses
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, to_address):
            return jsonify({"success": False, "error": f"Invalid to_address: {to_address}"}), 400
        
        for addr in cc:
            if not re.match(email_pattern, addr):
                return jsonify({"success": False, "error": f"Invalid cc address: {addr}"}), 400
        
        for addr in bcc:
            if not re.match(email_pattern, addr):
                return jsonify({"success": False, "error": f"Invalid bcc address: {addr}"}), 400
        
        # Return preview for user review
        preview_data = {
            "success": True,
            "preview": {
                "to_address": to_address,
                "cc": cc,
                "bcc": bcc,
                "subject": rendered_subject,
                "body": rendered_body,
                "is_template": bool(template_vars),
                "template_variables": template_vars
            },
            "message": "Review email content below. Click 'Send' to send immediately or 'Save Draft' to review later.",
            "actions": {
                "send": f"/api/email/send",
                "save_draft": f"/api/email/draft"
            }
        }
        
        logger.info(f"✅ Email preview generated for {to_address} (user: {user_id})")
        return jsonify(preview_data), 200
    
    except Exception as e:
        logger.error(f"❌ Email preview error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@email_send_bp.route("/send", methods=["POST"])
@require_auth
def send_email():
    """
    Send email immediately.
    
    Request body (same as /preview):
    {
        "to_address": "client@example.com",
        "subject": "Invoice - Thank You",
        "body": "Email content...",
        "cc": [...],
        "bcc": [...]
    }
    
    Returns:
    {
        "success": true,
        "sent_email_id": 123,
        "message": "Email sent successfully to client@example.com",
        "timestamp": "2026-09-24T12:30:45"
    }
    """
    try:
        ctx = current_user_context() or {}
        user_id = ctx.get("user_id")
        
        data = request.get_json() or {}
        to_address = (data.get("to_address") or "").strip()
        subject = (data.get("subject") or "").strip()
        body = (data.get("body") or "").strip()
        cc = data.get("cc") or []
        bcc = data.get("bcc") or []
        template_vars = data.get("template_variables") or {}
        
        # Validate
        if not to_address or not subject or not body:
            return jsonify({"success": False, "error": "Missing required fields"}), 400
        
        # Render templates if provided
        rendered_body = body
        rendered_subject = subject
        
        if template_vars:
            try:
                template = Template(body)
                rendered_body = template.render(**template_vars)
                template = Template(subject)
                rendered_subject = template.render(**template_vars)
            except TemplateError:
                pass
        
        # Send email
        success, error_msg = send_email_smtp(
            to_address=to_address,
            subject=rendered_subject,
            body=rendered_body,
            cc_addresses=cc,
            bcc_addresses=bcc
        )
        
        if not success:
            logger.warning(f"⚠️ Email send failed to {to_address}: {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg,
                "message": f"Failed to send email: {error_msg}"
            }), 500
        
        # Log sent email in database
        try:
            sent = SentEmail(
                recipient=to_address,
                cc_recipients=", ".join(cc) if cc else None,
                bcc_recipients=", ".join(bcc) if bcc else None,
                subject=rendered_subject,
                body=rendered_body,
                sent_timestamp=datetime.utcnow(),
                status="sent",
                user_id=user_id
            )
            db.session.add(sent)
            db.session.commit()
            sent_id = sent.id
        except Exception as db_err:
            logger.warning(f"⚠️ Could not log sent email: {db_err}")
            sent_id = None
        
        logger.info(f"✅ Email sent successfully to {to_address} (user: {user_id})")
        return jsonify({
            "success": True,
            "sent_email_id": sent_id,
            "message": f"✅ Email sent successfully to {to_address}",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Email send error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@email_send_bp.route("/draft", methods=["POST"])
@require_auth
def save_draft_email():
    """
    Save email as draft for later review/sending.
    
    Request body (same as /send):
    {
        "to_address": "client@example.com",
        "subject": "Invoice - Thank You",
        "body": "Email content...",
        "cc": [...],
        "bcc": [...],
        "notes": "Review before sending - ensure invoice is correct"
    }
    
    Returns:
    {
        "success": true,
        "draft_id": 42,
        "message": "Email saved as draft",
        "edit_url": "/api/email/draft/42"
    }
    """
    try:
        ctx = current_user_context() or {}
        user_id = ctx.get("user_id")
        
        data = request.get_json() or {}
        to_address = (data.get("to_address") or "").strip()
        subject = (data.get("subject") or "").strip()
        body = (data.get("body") or "").strip()
        cc = data.get("cc") or []
        bcc = data.get("bcc") or []
        notes = (data.get("notes") or "").strip()
        
        # Validate
        if not to_address or not subject or not body:
            return jsonify({"success": False, "error": "Missing required fields"}), 400
        
        # Create draft
        draft = DraftEmail(
            recipient=to_address,
            cc_recipients=", ".join(cc) if cc else None,
            bcc_recipients=", ".join(bcc) if bcc else None,
            subject=subject,
            body=body,
            notes=notes,
            status="draft",
            created_by_user_id=user_id
        )
        db.session.add(draft)
        db.session.commit()
        
        logger.info(f"📝 Draft email saved (ID: {draft.id}, to: {to_address}, user: {user_id})")
        return jsonify({
            "success": True,
            "draft_id": draft.id,
            "message": "✅ Email saved as draft",
            "edit_url": f"/api/email/draft/{draft.id}",
            "send_url": f"/api/email/draft/{draft.id}/send",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Draft save error: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@email_send_bp.route("/draft/<int:draft_id>", methods=["GET"])
@require_auth
def get_draft(draft_id):
    """Get draft email details for editing."""
    try:
        ctx = current_user_context() or {}
        user_id = ctx.get("user_id")
        
        draft = DraftEmail.query.get(draft_id)
        if not draft:
            return jsonify({"success": False, "error": "Draft not found"}), 404
        
        # Check permission (user can only see their own drafts unless admin)
        if not ctx.get("is_admin") and draft.created_by_user_id != user_id:
            return jsonify({"success": False, "error": "Access denied"}), 403
        
        return jsonify({
            "success": True,
            "draft": {
                "id": draft.id,
                "to_address": draft.recipient,
                "cc": draft.cc_recipients.split(", ") if draft.cc_recipients else [],
                "bcc": draft.bcc_recipients.split(", ") if draft.bcc_recipients else [],
                "subject": draft.subject,
                "body": draft.body,
                "notes": draft.notes,
                "status": draft.status,
                "created_at": draft.created_at.isoformat(),
                "updated_at": draft.updated_at.isoformat() if draft.updated_at else None
            }
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error retrieving draft: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@email_send_bp.route("/draft/<int:draft_id>/send", methods=["POST"])
@require_auth
def send_draft(draft_id):
    """Send a draft email."""
    try:
        ctx = current_user_context() or {}
        user_id = ctx.get("user_id")
        
        draft = DraftEmail.query.get(draft_id)
        if not draft:
            return jsonify({"success": False, "error": "Draft not found"}), 404
        
        # Check permission
        if not ctx.get("is_admin") and draft.created_by_user_id != user_id:
            return jsonify({"success": False, "error": "Access denied"}), 403
        
        # Get optional overrides from request body
        data = request.get_json() or {}
        to_address = (data.get("to_address") or draft.recipient).strip()
        subject = (data.get("subject") or draft.subject).strip()
        body = (data.get("body") or draft.body).strip()
        cc = data.get("cc") or (draft.cc_recipients.split(", ") if draft.cc_recipients else [])
        bcc = data.get("bcc") or (draft.bcc_recipients.split(", ") if draft.bcc_recipients else [])
        
        # Send
        success, error_msg = send_email_smtp(
            to_address=to_address,
            subject=subject,
            body=body,
            cc_addresses=cc,
            bcc_addresses=bcc
        )
        
        if not success:
            return jsonify({"success": False, "error": error_msg}), 500
        
        # Log and update draft status
        try:
            sent = SentEmail(
                recipient=to_address,
                cc_recipients=", ".join(cc) if cc else None,
                bcc_recipients=", ".join(bcc) if bcc else None,
                subject=subject,
                body=body,
                sent_timestamp=datetime.utcnow(),
                status="sent",
                user_id=user_id
            )
            db.session.add(sent)
            draft.status = "sent"
            db.session.commit()
        except Exception as db_err:
            logger.warning(f"⚠️ Error updating draft: {db_err}")
        
        logger.info(f"✅ Draft email sent (ID: {draft_id}, to: {to_address})")
        return jsonify({
            "success": True,
            "message": f"✅ Email sent from draft",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error sending draft: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
