"""API endpoints for email sync management and status tracking."""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from ..auth import require_auth
from ..models import StoredEmail, EmailSyncStatus, AutoReplySettings, DraftEmail
from ..extensions import db

logger = logging.getLogger(__name__)

# Create blueprint
sync_bp = Blueprint('email_sync', __name__, url_prefix='/api/email/sync')


@sync_bp.route('/status', methods=['GET'])
@require_auth
def get_sync_status():
    """
    Get current email sync status.
    
    Returns:
    {
        "success": true,
        "status": {
            "syncing": false,
            "status": "completed",
            "sync_type": "incremental",
            "last_sync_time": "2026-09-22T10:30:00",
            "next_sync_time": "2026-09-22T10:35:00",
            "total_emails": 150,
            "new_emails_count": 5,
            "emails_in_last_sync": 5,
            "sync_duration_seconds": 30,
            "error_message": null
        }
    }
    """
    try:
        from ..email_sync_service import get_sync_status_response
        return jsonify({
            "success": True,
            "status": get_sync_status_response()
        }), 200
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@sync_bp.route('/full', methods=['POST'])
@require_auth
def trigger_full_sync():
    """
    Trigger a full email sync (download all emails from all folders).
    
    This runs in the background. Use GET /status to check progress.
    
    Returns:
    {
        "success": true,
        "message": "Full email sync started (background)",
        "status": {...}
    }
    """
    try:
        from ..email_sync_service import start_full_sync
        return start_full_sync()
    except Exception as e:
        logger.error(f"Error triggering full sync: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@sync_bp.route('/continuous/start', methods=['POST'])
@require_auth
def start_continuous():
    """
    Start continuous email syncing (incremental sync at regular intervals).
    
    Returns:
    {
        "success": true,
        "message": "Continuous email sync started",
        "status": {...}
    }
    """
    try:
        from ..email_sync_service import start_continuous_sync
        return start_continuous_sync()
    except Exception as e:
        logger.error(f"Error starting continuous sync: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@sync_bp.route('/continuous/stop', methods=['POST'])
@require_auth
def stop_continuous():
    """
    Stop continuous email syncing.
    
    Returns:
    {
        "success": true,
        "message": "Continuous email sync stopped",
        "status": {...}
    }
    """
    try:
        from ..email_sync_service import stop_continuous_sync
        return stop_continuous_sync()
    except Exception as e:
        logger.error(f"Error stopping continuous sync: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@sync_bp.route('/new-emails', methods=['GET'])
@require_auth
def get_new_emails():
    """
    Get list of new emails (is_new=True) that haven't been processed.
    
    Query params:
    - limit: Max emails to return (default: 50)
    - folder: Filter by folder (default: all)
    
    Returns:
    {
        "success": true,
        "emails": [...],
        "count": 5
    }
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        folder = request.args.get('folder', None)
        
        query = StoredEmail.query.filter_by(is_new=True)
        
        if folder:
            query = query.filter_by(folder=folder)
        
        emails = query.order_by(StoredEmail.received_date.desc()).limit(limit).all()
        
        return jsonify({
            "success": True,
            "count": len(emails),
            "emails": [email.to_dict() for email in emails]
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting new emails: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@sync_bp.route('/mark-processed', methods=['POST'])
@require_auth
def mark_emails_processed():
    """
    Mark emails as processed (is_new=False).
    
    Request body:
    {
        "email_ids": [1, 2, 3],  // IDs to mark as processed
        "email_uids": ["uid1", "uid2"]  // OR UIDs to mark as processed
    }
    
    Returns:
    {
        "success": true,
        "count": 3,
        "message": "3 emails marked as processed"
    }
    """
    try:
        data = request.json or {}
        email_ids = data.get('email_ids', [])
        email_uids = data.get('email_uids', [])
        
        updated_count = 0
        
        if email_ids:
            updated_count += db.session.query(StoredEmail).filter(
                StoredEmail.id.in_(email_ids)
            ).update({StoredEmail.is_new: False})
        
        if email_uids:
            updated_count += db.session.query(StoredEmail).filter(
                StoredEmail.email_uid.in_(email_uids)
            ).update({StoredEmail.is_new: False})
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "count": updated_count,
            "message": f"{updated_count} emails marked as processed"
        }), 200
    
    except Exception as e:
        logger.error(f"Error marking emails as processed: {e}")
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@sync_bp.route('/auto-reply/execute', methods=['POST'])
@require_auth
def execute_auto_reply():
    """
    Execute auto-reply for new emails based on current settings.
    
    Request body (optional):
    {
        "limit": 10,  // Max emails to process
        "mode": "review"  // 'auto' (send immediately) or 'review' (create drafts)
    }
    
    Returns:
    {
        "success": true,
        "replied_count": 3,
        "total_processed": 5,
        "message": "Auto-replied to 3 emails"
    }
    """
    try:
        data = request.json or {}
        
        # Get auto-reply settings
        settings = AutoReplySettings.query.first()
        if not settings or not settings.enabled:
            return jsonify({
                "success": False,
                "error": "Auto-reply not enabled"
            }), 400
        
        # Build config from settings and request
        config = {
            'limit': data.get('limit', settings.reply_template and 10 or 5),
            'mode': data.get('mode', settings.mode or 'review'),
            'ai_instructions': settings.ai_instructions or 'Generate a professional response.'
        }
        
        from ..email_sync_service import apply_auto_reply_to_new_emails
        result = apply_auto_reply_to_new_emails(config)
        
        if result['status'] == 'success':
            return jsonify({
                "success": True,
                **result
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": result.get('message', 'Auto-reply failed')
            }), 500
    
    except Exception as e:
        logger.error(f"Error executing auto-reply: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@sync_bp.route('/history', methods=['GET'])
@require_auth
def get_sync_history():
    """
    Get sync history (for analytics/debugging).
    
    Returns:
    {
        "success": true,
        "history": [...]
    }
    """
    try:
        sync_status = EmailSyncStatus.query.first()
        
        if not sync_status:
            return jsonify({
                "success": True,
                "history": []
            }), 200
        
        return jsonify({
            "success": True,
            "history": [sync_status.to_dict()]
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting sync history: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@sync_bp.route('/stats', methods=['GET'])
@require_auth
def get_email_stats():
    """
    Get email statistics.
    
    Returns:
    {
        "success": true,
        "stats": {
            "total_emails": 150,
            "new_emails": 5,
            "unread_emails": 8,
            "by_folder": {
                "INBOX": 100,
                "Sent": 30,
                "Archive": 20
            }
        }
    }
    """
    try:
        total = StoredEmail.query.count()
        new = StoredEmail.query.filter_by(is_new=True).count()
        unread = StoredEmail.query.filter_by(is_read=False).count()
        
        # Group by folder
        folder_counts = {}
        for folder, count in db.session.query(
            StoredEmail.folder, 
            db.func.count(StoredEmail.id)
        ).group_by(StoredEmail.folder).all():
            folder_counts[folder] = count
        
        return jsonify({
            "success": True,
            "stats": {
                "total_emails": total,
                "new_emails": new,
                "unread_emails": unread,
                "by_folder": folder_counts
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting email stats: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@sync_bp.route('/sender-type/<int:email_id>', methods=['GET'])
@require_auth
def get_sender_type(email_id):
    """
    Detect and return sender type for an email.
    
    Returns:
    {
        "success": true,
        "email_id": 123,
        "sender_type": "client",
        "sender_info": {
            "name": "John Smith",
            "email": "john@company.com"
        },
        "message": "Detected as: client"
    }
    """
    try:
        from ..email_intelligence import SenderDetector
        
        email = StoredEmail.query.get(email_id)
        if not email:
            return jsonify({
                "success": False,
                "error": f"Email {email_id} not found"
            }), 404
        
        sender_type = SenderDetector.detect_sender_type(
            email.from_address,
            email.subject or "",
            email.body or ""
        )
        sender_info = SenderDetector.extract_sender_info(email.from_address)
        
        return jsonify({
            "success": True,
            "email_id": email_id,
            "sender_type": sender_type,
            "sender_info": sender_info,
            "message": f"Detected as: {sender_type}"
        }), 200
    
    except Exception as e:
        logger.error(f"Error detecting sender type: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@sync_bp.route('/drafts/pending', methods=['GET'])
@require_auth
def get_pending_drafts():
    """
    Get all pending auto-reply draft emails waiting for review.
    
    Query params:
    - sender_type: Filter by sender type (client, employee, vendor, etc)
    - limit: Max results (default: 50)
    - page: Page number (default: 1)
    
    Returns:
    {
        "success": true,
        "drafts": [
            {
                "id": 456,
                "to_address": "client@company.com",
                "subject": "Re: Invoice Request",
                "body": "Thank you for your email...",
                "sender_type": "client",
                "related_email_id": 123,
                "created_at": "2026-09-24T12:00:00"
            }
        ],
        "count": 3,
        "total": 3
    }
    """
    try:
        sender_type = request.args.get('sender_type', None)
        limit = request.args.get('limit', 50, type=int)
        page = request.args.get('page', 1, type=int)
        
        query = DraftEmail.query.filter_by(status='draft')
        
        if sender_type:
            # Filter by sender_type in metadata
            all_drafts = query.all()
            filtered_drafts = []
            for draft in all_drafts:
                metadata = draft.metadata or {}
                if metadata.get('sender_type') == sender_type:
                    filtered_drafts.append(draft)
            
            total = len(filtered_drafts)
            start = (page - 1) * limit
            drafts = filtered_drafts[start:start + limit]
        else:
            total = query.count()
            drafts = query.offset((page - 1) * limit).limit(limit).all()
        
        return jsonify({
            "success": True,
            "drafts": [{
                "id": draft.id,
                "to_address": draft.to_address,
                "subject": draft.subject,
                "body": draft.body[:200] + "..." if len(draft.body or "") > 200 else draft.body,
                "sender_type": (draft.metadata or {}).get('sender_type', 'unknown'),
                "related_email_id": (draft.metadata or {}).get('related_email_id'),
                "created_at": draft.created_at.isoformat() if draft.created_at else None
            } for draft in drafts],
            "count": len(drafts),
            "total": total,
            "page": page
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting pending drafts: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@sync_bp.route('/drafts/<int:draft_id>/send', methods=['POST'])
@require_auth
def send_draft(draft_id):
    """
    Send a pending draft and mark it as sent.
    
    Returns:
    {
        "success": true,
        "draft_id": 456,
        "email_sent_id": 789,
        "message": "Draft sent successfully to client@company.com"
    }
    """
    try:
        from .email_scheduling import send_email_smtp
        
        draft = DraftEmail.query.get(draft_id)
        if not draft:
            return jsonify({
                "success": False,
                "error": f"Draft {draft_id} not found"
            }), 404
        
        if draft.status != 'draft':
            return jsonify({
                "success": False,
                "error": f"Draft is already {draft.status}, cannot send"
            }), 400
        
        # Send the email
        success, error_msg = send_email_smtp(
            draft.to_address,
            draft.subject,
            draft.body
        )
        
        if not success:
            return jsonify({
                "success": False,
                "error": f"Failed to send email: {error_msg}"
            }), 500
        
        # Mark draft as sent
        draft.status = 'sent'
        draft.sent_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "draft_id": draft_id,
            "message": f"Draft sent successfully to {draft.to_address}"
        }), 200
    
    except Exception as e:
        logger.error(f"Error sending draft: {e}")
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@sync_bp.route('/drafts/<int:draft_id>/discard', methods=['DELETE'])
@require_auth
def discard_draft(draft_id):
    """
    Discard a pending draft.
    
    Returns:
    {
        "success": true,
        "message": "Draft discarded"
    }
    """
    try:
        draft = DraftEmail.query.get(draft_id)
        if not draft:
            return jsonify({
                "success": False,
                "error": f"Draft {draft_id} not found"
            }), 404
        
        draft.status = 'discarded'
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Draft discarded"
        }), 200
    
    except Exception as e:
        logger.error(f"Error discarding draft: {e}")
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
