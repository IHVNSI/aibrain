"""API endpoints for email storage and retrieval from database with pagination."""
import logging
from flask import Blueprint, request, jsonify
from ..extensions import db
from ..auth import require_auth
from ..models import StoredEmail, SentEmail

logger = logging.getLogger(__name__)

storage_email_bp = Blueprint('email_storage', __name__, url_prefix='/api/email/storage')


@storage_email_bp.route('/inbox', methods=['GET'])
@require_auth
def get_inbox_emails():
    """
    Get all emails (read and unread) from INBOX folder with pagination.
    
    Query params:
    - page: Page number (default: 1, starts at 1)
    - per_page: Items per page (default: 20, max: 100)
    - unread_only: If 'true', only unread emails (default: false)
    - sort_by: 'date' (default) or 'subject'
    - sort_order: 'desc' (default) or 'asc'
    
    Returns:
        {
            "success": true,
            "emails": [...],
            "pagination": {
                "page": 1,
                "per_page": 20,
                "total": 150,
                "total_pages": 8,
                "has_next": true,
                "has_prev": false
            }
        }
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        sort_by = request.args.get('sort_by', 'date')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Validate pagination
        per_page = min(per_page, 100)
        if per_page < 1:
            per_page = 20
        if page < 1:
            page = 1
        
        # Build query
        query = StoredEmail.query.filter_by(folder='INBOX')
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        # Sort
        if sort_by == 'subject':
            sort_column = StoredEmail.subject
        else:  # date
            sort_column = StoredEmail.received_date
        
        if sort_order == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
        
        # Paginate
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        emails = [email.to_dict() for email in paginated.items]
        
        return jsonify({
            "success": True,
            "emails": emails,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": paginated.total,
                "total_pages": paginated.pages,
                "has_next": paginated.has_next,
                "has_prev": paginated.has_prev
            },
            "message": f"Loaded {len(emails)} emails (page {page} of {paginated.pages})"
        }), 200
    
    except Exception as e:
        logger.error(f"Error fetching inbox emails: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@storage_email_bp.route('/folder/<path:folder_name>', methods=['GET'])
@require_auth
def get_folder_emails(folder_name):
    """
    Get all emails from a specific folder with pagination.
    
    URL params:
    - folder_name: Folder name (e.g., 'INBOX', 'INBOX.Sent', 'INBOX.Trash')
    
    Query params:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    - unread_only: If 'true', only unread emails (default: false)
    - sort_by: 'date' (default) or 'subject'
    - sort_order: 'desc' (default) or 'asc'
    
    Returns:
        Same as /inbox endpoint
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        sort_by = request.args.get('sort_by', 'date')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Validate pagination
        per_page = min(per_page, 100)
        if per_page < 1:
            per_page = 20
        if page < 1:
            page = 1
        
        # Decode folder name (URL encoded)
        import urllib.parse
        folder_name = urllib.parse.unquote(folder_name)
        
        # Build query
        query = StoredEmail.query.filter_by(folder=folder_name)
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        # Sort
        if sort_by == 'subject':
            sort_column = StoredEmail.subject
        else:
            sort_column = StoredEmail.received_date
        
        if sort_order == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
        
        # Paginate
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        emails = [email.to_dict() for email in paginated.items]
        
        return jsonify({
            "success": True,
            "folder": folder_name,
            "emails": emails,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": paginated.total,
                "total_pages": paginated.pages,
                "has_next": paginated.has_next,
                "has_prev": paginated.has_prev
            },
            "message": f"Loaded {len(emails)} emails from {folder_name} (page {page} of {paginated.pages})"
        }), 200
    
    except Exception as e:
        logger.error(f"Error fetching folder emails: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@storage_email_bp.route('/sent', methods=['GET'])
@require_auth
def get_sent_emails():
    """
    Get all sent emails (AI responses and manual sends) with pagination.
    
    Query params:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    - ai_only: If 'true', only AI-generated emails (default: false)
    - sort_by: 'date' (default) or 'subject'
    - sort_order: 'desc' (default) or 'asc'
    
    Returns:
        {
            "success": true,
            "emails": [...sent emails with ai_generated flag...],
            "pagination": {...}
        }
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        ai_only = request.args.get('ai_only', 'false').lower() == 'true'
        sort_by = request.args.get('sort_by', 'date')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Validate pagination
        per_page = min(per_page, 100)
        if per_page < 1:
            per_page = 20
        if page < 1:
            page = 1
        
        # Build query
        query = SentEmail.query.filter_by(status='sent')
        
        if ai_only:
            query = query.filter_by(ai_generated=True)
        
        # Sort
        if sort_by == 'subject':
            sort_column = SentEmail.subject
        else:
            sort_column = SentEmail.sent_at
        
        if sort_order == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
        
        # Paginate
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        emails = [email.to_dict() for email in paginated.items]
        
        return jsonify({
            "success": True,
            "emails": emails,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": paginated.total,
                "total_pages": paginated.pages,
                "has_next": paginated.has_next,
                "has_prev": paginated.has_prev
            },
            "message": f"Loaded {len(emails)} sent emails (page {page} of {paginated.pages})"
        }), 200
    
    except Exception as e:
        logger.error(f"Error fetching sent emails: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@storage_email_bp.route('/sent/<int:email_id>', methods=['DELETE'])
@require_auth
def delete_sent_email(email_id):
    """
    Delete a sent email by ID.
    
    Args:
        email_id: ID of sent email to delete
    
    Returns:
        {
            "success": true,
            "message": "Email deleted successfully",
            "deleted_id": 123
        }
    """
    try:
        email = SentEmail.query.get(email_id)
        
        if not email:
            return jsonify({
                "success": False,
                "error": "Sent email not found"
            }), 404
        
        db.session.delete(email)
        db.session.commit()
        
        logger.info(f"Deleted sent email ID {email_id}: {email.subject}")
        
        return jsonify({
            "success": True,
            "message": "Email deleted successfully",
            "deleted_id": email_id
        })
    
    except Exception as e:
        logger.error(f"Error deleting sent email: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@storage_email_bp.route('/search', methods=['GET'])
@require_auth
def search_emails():
    """
    Search emails across all folders.
    
    Query params:
    - q: Search query (searches in subject, body, from_address)
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    - folder: Filter by folder (optional)
    - sort_order: 'desc' (default) or 'asc'
    
    Returns:
        Same as /inbox endpoint with search results
    """
    try:
        q = request.args.get('q', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        folder = request.args.get('folder', None)
        sort_order = request.args.get('sort_order', 'desc')
        
        if not q:
            return jsonify({
                "success": False,
                "error": "Search query cannot be empty"
            }), 400
        
        # Validate pagination
        per_page = min(per_page, 100)
        if per_page < 1:
            per_page = 20
        if page < 1:
            page = 1
        
        # Build query
        query = StoredEmail.query
        
        # Search in multiple fields
        search_term = f"%{q}%"
        from sqlalchemy import or_
        query = query.filter(
            or_(
                StoredEmail.subject.ilike(search_term),
                StoredEmail.body.ilike(search_term),
                StoredEmail.from_address.ilike(search_term)
            )
        )
        
        # Filter by folder if specified
        if folder:
            query = query.filter_by(folder=folder)
        
        # Sort by date
        if sort_order == 'asc':
            query = query.order_by(StoredEmail.received_date.asc())
        else:
            query = query.order_by(StoredEmail.received_date.desc())
        
        # Paginate
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        emails = [email.to_dict() for email in paginated.items]
        
        return jsonify({
            "success": True,
            "search_query": q,
            "emails": emails,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": paginated.total,
                "total_pages": paginated.pages,
                "has_next": paginated.has_next,
                "has_prev": paginated.has_prev
            },
            "message": f"Found {paginated.total} results for '{q}' (page {page} of {paginated.pages})"
        }), 200
    
    except Exception as e:
        logger.error(f"Error searching emails: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@storage_email_bp.route('/<int:email_id>', methods=['GET'])
@require_auth
def get_email_detail(email_id):
    """Get detailed view of a single email from database."""
    try:
        email = StoredEmail.query.filter_by(id=email_id).first()
        
        if not email:
            return jsonify({
                "success": False,
                "error": "Email not found"
            }), 404
        
        # Mark as read
        email.is_read = True
        db.session.commit()
        
        return jsonify({
            "success": True,
            "email": email.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Error fetching email detail: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@storage_email_bp.route('/<int:email_id>/mark-read', methods=['PUT'])
@require_auth
def mark_email_read(email_id):
    """Mark email as read."""
    try:
        email = StoredEmail.query.filter_by(id=email_id).first()
        
        if not email:
            return jsonify({
                "success": False,
                "error": "Email not found"
            }), 404
        
        email.is_read = True
        db.session.commit()
        
        return jsonify({
            "success": True,
            "email": email.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Error marking email as read: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@storage_email_bp.route('/delete-bulk', methods=['POST'])
@require_auth
def delete_bulk_stored_emails():
    """
    Delete multiple stored emails in bulk.
    
    Request body:
        {
            "email_ids": [1, 2, 3, ...]
        }
    
    Returns:
        {
            "success": true,
            "deleted_count": 3,
            "message": "Deleted 3 emails"
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        email_ids = data.get('email_ids', [])
        
        if not email_ids or not isinstance(email_ids, list):
            return jsonify({
                "success": False,
                "error": "email_ids must be a non-empty list"
            }), 400
        
        # Limit to 1000 emails per request to prevent abuse
        if len(email_ids) > 1000:
            return jsonify({
                "success": False,
                "error": "Cannot delete more than 1000 emails at once"
            }), 400
        
        # Delete emails by IDs
        deleted_count = StoredEmail.query.filter(StoredEmail.id.in_(email_ids)).delete()
        db.session.commit()
        
        logger.info(f"Bulk deleted {deleted_count} stored emails: {email_ids}")
        
        return jsonify({
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Deleted {deleted_count} email(s) successfully"
        }), 200
    
    except Exception as e:
        logger.error(f"Error bulk deleting stored emails: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@storage_email_bp.route('/sent/delete-bulk', methods=['POST'])
@require_auth
def delete_bulk_sent_emails():
    """
    Delete multiple sent emails in bulk.
    
    Request body:
        {
            "email_ids": [1, 2, 3, ...]
        }
    
    Returns:
        {
            "success": true,
            "deleted_count": 3,
            "message": "Deleted 3 emails"
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        email_ids = data.get('email_ids', [])
        
        if not email_ids or not isinstance(email_ids, list):
            return jsonify({
                "success": False,
                "error": "email_ids must be a non-empty list"
            }), 400
        
        # Limit to 1000 emails per request to prevent abuse
        if len(email_ids) > 1000:
            return jsonify({
                "success": False,
                "error": "Cannot delete more than 1000 emails at once"
            }), 400
        
        # Delete emails by IDs
        deleted_count = SentEmail.query.filter(SentEmail.id.in_(email_ids)).delete()
        db.session.commit()
        
        logger.info(f"Bulk deleted {deleted_count} sent emails: {email_ids}")
        
        return jsonify({
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Deleted {deleted_count} email(s) successfully"
        }), 200
    
    except Exception as e:
        logger.error(f"Error bulk deleting sent emails: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@storage_email_bp.route('/debug/test-fetch', methods=['GET'])
@require_auth
def debug_test_fetch():
    """
    DEBUG ENDPOINT: Test email fetching directly from IMAP server.
    Shows what emails are available in Gmail INBOX.
    """
    try:
        from ..email_config import EmailConfig
        
        logger.info("DEBUG: Testing email fetch...")
        
        email_service = EmailConfig.get_email_service()
        if not email_service:
            return jsonify({
                "success": False,
                "error": "Email service not configured"
            }), 500
        
        # Test connection
        try:
            email_service.connect()
            logger.info("DEBUG: Connection successful")
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Connection failed: {str(e)}"
            }), 500
        
        # Get folder list
        folders = email_service.get_folder_list()
        logger.info(f"DEBUG: Found {len(folders)} folders: {folders}")
        
        # Try to fetch from INBOX
        emails = email_service.get_all_emails(folder='INBOX', limit=50)
        logger.info(f"DEBUG: Fetched {len(emails)} emails from INBOX")
        
        # Count stored emails
        stored_count = StoredEmail.query.count()
        logger.info(f"DEBUG: {stored_count} emails stored in database")
        
        email_service.disconnect()
        
        return jsonify({
            "success": True,
            "folders_found": len(folders),
            "inbox_emails_count": len(emails),
            "inbox_sample": emails[:3] if emails else [],
            "stored_in_db": stored_count
        })
    
    except Exception as e:
        logger.error(f"DEBUG: Test fetch failed: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
        
        # Delete emails by IDs
        deleted_count = SentEmail.query.filter(SentEmail.id.in_(email_ids)).delete()
        db.session.commit()
        
        logger.info(f"Bulk deleted {deleted_count} sent emails: {email_ids}")
        
        return jsonify({
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Deleted {deleted_count} email(s) successfully"
        }), 200
    
    except Exception as e:
        logger.error(f"Error bulk deleting sent emails: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
