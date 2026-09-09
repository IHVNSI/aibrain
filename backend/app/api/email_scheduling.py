"""API endpoints for email management and task scheduling."""
import logging
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from functools import wraps
import os

from ..extensions import db
from ..auth import require_auth
from ..email_service import EmailService, EmailConfig
from ..scheduler_service import TaskScheduler, parse_natural_language_schedule
from ..llm.factory import build_llm

logger = logging.getLogger(__name__)

# Create blueprints
email_bp = Blueprint('email', __name__, url_prefix='/api/email')
scheduler_bp = Blueprint('scheduler', __name__, url_prefix='/api/scheduler')

# Initialize task scheduler (global instance)
task_scheduler = None


def get_task_scheduler() -> TaskScheduler:
    """Get or create task scheduler instance."""
    global task_scheduler
    if task_scheduler is None:
        task_scheduler = TaskScheduler()
    return task_scheduler


# ============================================================================
# EMAIL ENDPOINTS
# ============================================================================

@email_bp.route('/unread', methods=['GET'])
@require_auth
def get_unread_emails():
    """
    Get unread emails from the configured email account and store in database.
    
    Query params:
    - limit: Max emails to return (default: 50)
    - folder: Email folder (default: INBOX)
    - store: Whether to store in database (default: true)
    
    Returns:
        {
            "success": true,
            "emails": [...downloaded emails...],
            "count": 5,
            "stored": 3,
            "message": "Retrieved 5 unread emails, stored 3 new"
        }
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        folder = request.args.get('folder', 'INBOX')
        store = request.args.get('store', 'true').lower() == 'true'
        
        logger.info(f"🔄 Fetching {limit} unread emails from {folder}...")
        
        # Get email service with connection
        email_service = EmailConfig.get_email_service()
        if not email_service:
            logger.error("Email service not configured")
            return jsonify({
                "success": False,
                "error": "Email service not configured. Set EMAIL_ADDRESS, EMAIL_PASSWORD, EMAIL_IMAP_SERVER in .env",
                "setup_guide": "See docs/EMAIL_CONFIGURATION_GUIDE.md for setup"
            }), 400
        
        # Fetch unread emails
        try:
            emails = email_service.get_unread_emails(limit=limit, folder=folder)
            logger.info(f"✓ Retrieved {len(emails)} unread emails from {folder}")
        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": f"Failed to connect to email server: {str(e)}",
                "suggestion": "Verify EMAIL_IMAP_SERVER, EMAIL_ADDRESS, EMAIL_PASSWORD are correct"
            }), 400
        finally:
            try:
                email_service.disconnect()
            except:
                pass
        
        # Store in database if requested
        stored_count = 0
        if store and emails:
            try:
                from ..models import StoredEmail
                from datetime import datetime
                
                for email in emails:
                    # Check if email already exists
                    existing = StoredEmail.query.filter_by(email_uid=email['id']).first()
                    if not existing:
                        try:
                            received_dt = datetime.fromisoformat(email['date']) if email.get('date') else datetime.now()
                        except:
                            received_dt = datetime.now()
                        
                        stored_email = StoredEmail(
                            email_uid=email['id'],
                            from_address=email.get('from', ''),
                            subject=email.get('subject', ''),
                            body=email.get('text', ''),
                            html_body=email.get('html', ''),
                            received_date=received_dt,
                            is_read=not email.get('is_unread', False),
                            folder=folder
                        )
                        db.session.add(stored_email)
                        stored_count += 1
                
                if stored_count > 0:
                    db.session.commit()
                    logger.info(f"✓ Stored {stored_count} new emails in database")
            except Exception as e:
                logger.error(f"Error storing emails: {e}", exc_info=True)
                db.session.rollback()
        
        return jsonify({
            "success": True,
            "emails": emails,
            "count": len(emails),
            "stored": stored_count,
            "message": f"Retrieved {len(emails)} unread emails, stored {stored_count} new"
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting unread emails: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@email_bp.route('/sync', methods=['POST'])
@require_auth
def sync_emails():
    """
    Sync all emails from configured email account to database.
    Downloads both unread and read emails.
    
    Body (optional):
    {
        "days_back": 30,  # Download emails from last N days (default: 30)
        "limit": 100      # Max emails to download (default: 100)
    }
    
    Returns:
        {
            "success": true,
            "total_downloaded": 100,
            "total_stored": 45,
            "new_emails": 12,
            "message": "Synced 100 emails, stored 45 in database"
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        days_back = data.get('days_back', 30)
        limit = data.get('limit', 100)
        
        logger.info(f"🔄 Syncing emails from last {days_back} days (limit: {limit})...")
        
        # Get email service
        email_service = EmailConfig.get_email_service()
        if not email_service:
            return jsonify({
                "success": False,
                "error": "Email service not configured"
            }), 400
        
        # Fetch emails by date range
        try:
            emails = email_service.get_emails_by_date_range(days_back=days_back, limit=limit)
            logger.info(f"✓ Retrieved {len(emails)} emails from last {days_back} days")
        except Exception as e:
            logger.error(f"Failed to sync emails: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 400
        finally:
            try:
                email_service.disconnect()
            except:
                pass
        
        # Store in database
        stored_count = 0
        new_count = 0
        try:
            from ..models import StoredEmail
            from datetime import datetime
            
            for email in emails:
                existing = StoredEmail.query.filter_by(email_uid=email['id']).first()
                if not existing:
                    try:
                        received_dt = datetime.fromisoformat(email['date']) if email.get('date') else datetime.now()
                    except:
                        received_dt = datetime.now()
                    
                    stored_email = StoredEmail(
                        email_uid=email['id'],
                        from_address=email.get('from', ''),
                        subject=email.get('subject', ''),
                        body=email.get('text', ''),
                        html_body=email.get('html', ''),
                        received_date=received_dt,
                        is_read=email.get('is_unread', False) == False,
                        folder='INBOX'
                    )
                    db.session.add(stored_email)
                    new_count += 1
                stored_count += 1
            
            if new_count > 0:
                db.session.commit()
                logger.info(f"✓ Synced {new_count} new emails to database")
        except Exception as e:
            logger.error(f"Error syncing emails: {e}", exc_info=True)
            db.session.rollback()
        
        return jsonify({
            "success": True,
            "total_downloaded": len(emails),
            "total_stored": stored_count,
            "new_emails": new_count,
            "message": f"Synced {len(emails)} emails, stored {new_count} new in database"
        }), 200
        
    except Exception as e:
        logger.error(f"Email sync error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@email_bp.route('/list', methods=['GET'])
@require_auth
def list_stored_emails():
    """
    List emails stored in database.
    
    Query params:
    - limit: Max emails to return (default: 50)
    - offset: Skip N emails (default: 0)
    - unread_only: Only show unread (default: false)
    
    Returns:
        {
            "success": true,
            "emails": [...],
            "total": 150,
            "limit": 50
        }
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        from ..models import StoredEmail
        
        query = StoredEmail.query.order_by(StoredEmail.received_date.desc())
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        total = query.count()
        emails = query.limit(limit).offset(offset).all()
        
        return jsonify({
            "success": True,
            "emails": [email.to_dict() for email in emails],
            "total": total,
            "limit": limit,
            "offset": offset
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing emails: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@email_bp.route('/search', methods=['GET'])
@require_auth
def search_emails():
    """
    Search emails by query.
    
    Query params:
    - q: Search query (subject or content)
    - limit: Max results (default: 10)
    
    Returns:
        {"success": true, "emails": [...], "count": 5}
    """
    try:
        query = request.args.get('q', '')
        limit = request.args.get('limit', 10, type=int)
        
        if not query:
            return jsonify({
                "success": False,
                "error": "Search query required"
            }), 400
        
        email_service = EmailConfig.get_email_service()
        if not email_service:
            return jsonify({
                "success": False,
                "error": "Email service not configured"
            }), 400
        
        emails = email_service.search_emails(query=query, limit=limit)
        email_service.disconnect()
        
        return jsonify({
            "success": True,
            "emails": emails,
            "count": len(emails)
        }), 200
    
    except Exception as e:
        logger.error(f"Error searching emails: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@email_bp.route('/mark-read/<email_id>', methods=['POST'])
@require_auth
def mark_email_read(email_id):
    """Mark an email as read."""
    try:
        email_service = EmailConfig.get_email_service()
        if not email_service:
            return jsonify({"success": False, "error": "Email service not configured"}), 400
        
        success = email_service.mark_as_read(email_id)
        email_service.disconnect()
        
        return jsonify({
            "success": success,
            "message": f"Email marked as {'read' if success else 'unread'}"
        }), 200 if success else 500
    
    except Exception as e:
        logger.error(f"Error marking email: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@email_bp.route('/respond', methods=['POST'])
@require_auth
def respond_to_email():
    """
    Send an AI-generated response to an email.
    
    Request body:
    {
        "email_from": "sender@example.com",
        "subject": "Original email subject",
        "body": "Original email body",
        "custom_prompt": "Optional custom instruction for AI response"
    }
    
    Returns:
        {
            "success": true,
            "message": "Response sent successfully",
            "response": "Generated response text"
        }
    """
    try:
        data = request.get_json()
        email_from = data.get('email_from')
        subject = data.get('subject')
        body = data.get('body')
        custom_prompt = data.get('custom_prompt', '')
        
        if not email_from or not subject or not body:
            return jsonify({"success": False, "error": "email_from, subject, and body are required"}), 400
        
        # Get LLM
        llm = build_llm()
        if not llm:
            return jsonify({"success": False, "error": "LLM not configured"}), 500
        
        # Build prompt
        base_prompt = f"""You are a professional email assistant. 

The user received this email:

From: {email_from}
Subject: {subject}

Body:
{body}

Please generate a professional, concise response email. 
Keep it brief (2-3 sentences), professional, and helpful.
Only return the email body, no subject line or formatting."""
        
        if custom_prompt:
            base_prompt += f"\n\nAdditional instructions: {custom_prompt}"
        
        # Generate response using LLM chat interface
        messages = [{"role": "user", "content": base_prompt}]
        response_text = llm.chat(messages)
        
        if not response_text:
            return jsonify({"success": False, "error": "Failed to generate response"}), 500
        
        # Send email
        reply_subject = f"Re: {subject}"
        if send_email_smtp(email_from, reply_subject, response_text):
            logger.info(f"✓ AI response sent to {email_from}")
            return jsonify({
                "success": True,
                "message": "Response sent successfully",
                "response": response_text,
                "recipient": email_from,
                "subject": reply_subject
            }), 200
        else:
            return jsonify({"success": False, "error": "Failed to send email"}), 500
    
    except Exception as e:
        logger.error(f"Error responding to email: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@email_bp.route('/folders', methods=['GET'])
@require_auth
def get_email_folders():
    """Get list of email folders."""
    try:
        email_service = EmailConfig.get_email_service()
        if not email_service:
            return jsonify({"success": False, "error": "Email service not configured"}), 400
        
        folders = email_service.get_folder_list()
        email_service.disconnect()
        
        return jsonify({
            "success": True,
            "folders": folders,
            "count": len(folders)
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting folders: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@email_bp.route('/config', methods=['GET'])
@require_auth
def get_email_config():
    """Get current email configuration (password masked)."""
    try:
        config = {
            "email_address": os.getenv('EMAIL_ADDRESS', ''),
            "email_provider": os.getenv('EMAIL_PROVIDER', 'gmail'),
            "imap_server": os.getenv('EMAIL_IMAP_SERVER', ''),
            "imap_port": os.getenv('EMAIL_IMAP_PORT', '993'),
            "imap_tls": os.getenv('EMAIL_IMAP_TLS', 'true').lower() == 'true',
            "smtp_server": os.getenv('EMAIL_SMTP_SERVER', ''),
            "smtp_port": os.getenv('EMAIL_SMTP_PORT', '587'),
            "smtp_tls": os.getenv('EMAIL_SMTP_TLS', 'true').lower() == 'true',
            "check_interval": os.getenv('EMAIL_CHECK_INTERVAL', '5'),
            "fetch_limit": os.getenv('EMAIL_FETCH_LIMIT', '10'),
            "password_configured": bool(os.getenv('EMAIL_PASSWORD', '')),
        }
        
        # Provider IMAP/SMTP presets
        providers = {
            'gmail': {
                'imap_server': 'imap.gmail.com',
                'imap_port': 993,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
            },
            'outlook': {
                'imap_server': 'outlook.office365.com',
                'imap_port': 993,
                'smtp_server': 'smtp.office365.com',
                'smtp_port': 587,
            },
            'yahoo': {
                'imap_server': 'imap.mail.yahoo.com',
                'imap_port': 993,
                'smtp_server': 'smtp.mail.yahoo.com',
                'smtp_port': 465,
            },
            'icloud': {
                'imap_server': 'imap.mail.me.com',
                'imap_port': 993,
                'smtp_server': 'smtp.mail.me.com',
                'smtp_port': 587,
            },
        }
        
        return jsonify({
            "success": True,
            "config": config,
            "providers": providers,
            "available_providers": list(providers.keys())
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting email config: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@email_bp.route('/config', methods=['POST'])
@require_auth
def update_email_config():
    """
    Update email configuration.
    
    Request body:
    {
        "email_address": "email@example.com",
        "email_password": "password",
        "email_provider": "gmail",
        "imap_server": "imap.example.com",
        "imap_port": 993,
        "imap_tls": true,
        "smtp_server": "smtp.example.com",
        "smtp_port": 587,
        "smtp_tls": true,
        "test_connection": true  // Optional: test the config
    }
    """
    try:
        from ..db_migration import _update_env_file
        
        data = request.json or {}
        
        # Extract configuration
        email_address = data.get('email_address', '').strip()
        email_password = data.get('email_password', '').strip()
        email_provider = data.get('email_provider', 'gmail').lower()
        imap_server = data.get('imap_server', '').strip()
        imap_port = data.get('imap_port', 993)
        imap_tls = data.get('imap_tls', True)
        smtp_server = data.get('smtp_server', '').strip()
        smtp_port = data.get('smtp_port', 587)
        smtp_tls = data.get('smtp_tls', True)
        check_interval = data.get('check_interval', 5)
        fetch_limit = data.get('fetch_limit', 10)
        test_connection = data.get('test_connection', False)
        
        # Validate required fields
        if not email_address:
            return jsonify({"success": False, "error": "Email address is required"}), 400
        
        if not email_password:
            return jsonify({"success": False, "error": "Email password is required"}), 400
        
        # Update environment variables
        env_updates = {
            'EMAIL_ADDRESS': email_address,
            'EMAIL_PASSWORD': email_password,
            'EMAIL_PROVIDER': email_provider,
            'EMAIL_IMAP_SERVER': imap_server,
            'EMAIL_IMAP_PORT': str(imap_port),
            'EMAIL_IMAP_TLS': str(imap_tls).lower(),
            'EMAIL_SMTP_SERVER': smtp_server,
            'EMAIL_SMTP_PORT': str(smtp_port),
            'EMAIL_SMTP_TLS': str(smtp_tls).lower(),
            'EMAIL_CHECK_INTERVAL': str(check_interval),
            'EMAIL_FETCH_LIMIT': str(fetch_limit),
        }
        
        # Update .env file - call _update_env_file for each key-value pair
        for key, value in env_updates.items():
            _update_env_file(key, value)
        
        # Update environment variables in current process
        for key, value in env_updates.items():
            os.environ[key] = value
        
        # Test connection if requested
        test_result = None
        if test_connection:
            try:
                from ..email_service import EmailService
                service = EmailService(imap_server, email_address, email_password)
                if service.connect():
                    test_result = "✓ Connection successful"
                    service.disconnect()
                else:
                    test_result = "✗ Connection failed"
            except Exception as e:
                test_result = f"✗ Connection error: {str(e)}"
        
        return jsonify({
            "success": True,
            "message": "Email configuration updated",
            "test_result": test_result,
            "config": {
                "email_address": email_address,
                "email_provider": email_provider,
                "imap_server": imap_server,
                "smtp_server": smtp_server,
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error updating email config: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# SCHEDULER ENDPOINTS
# ============================================================================

@scheduler_bp.route('/tasks', methods=['GET'])
@require_auth
def get_all_tasks():
    """
    Get all scheduled tasks.
    
    Returns:
        {
            "success": true,
            "tasks": [
                {
                    "id": 1,
                    "name": "Check emails daily",
                    "task_type": "email_check",
                    "is_active": true,
                    "last_run": "2025-08-14T10:00:00",
                    "next_run": "2025-08-15T10:00:00"
                }
            ],
            "count": 3
        }
    """
    try:
        scheduler = get_task_scheduler()
        tasks = scheduler.get_all_tasks()
        
        return jsonify({
            "success": True,
            "tasks": tasks,
            "count": len(tasks)
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route('/tasks', methods=['POST'])
@require_auth
def create_task():
    """
    Create a new scheduled task.
    
    Request body:
    {
        "name": "Read emails daily",
        "task_type": "email_check",
        "instruction": "read email at 10 AM",
        "description": "Check for new emails every morning at 10 AM",
        "task_config": {
            "email_folder": "INBOX",
            "filter": "unread"
        }
    }
    
    Returns:
        {"success": true, "task": {...}, "message": "Task created"}
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['name', 'task_type', 'instruction']
        if not all(k in data for k in required):
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {required}"
            }), 400
        
        # Parse natural language instruction to schedule
        schedule_config = parse_natural_language_schedule(data['instruction'])
        if not schedule_config:
            return jsonify({
                "success": False,
                "error": "Could not parse scheduling instruction"
            }), 400
        
        # Create task
        scheduler = get_task_scheduler()
        task = scheduler.create_task(
            name=data['name'],
            task_type=data['task_type'],
            natural_language_instruction=data['instruction'],
            schedule_config=schedule_config,
            task_config=data.get('task_config', {}),
            description=data.get('description'),
            created_by=request.ctx.get('user_id') if hasattr(request, 'ctx') else None
        )
        
        if not task:
            return jsonify({
                "success": False,
                "error": "Failed to create task"
            }), 500
        
        return jsonify({
            "success": True,
            "task": {
                'id': task.id,
                'name': task.name,
                'task_type': task.task_type,
                'instruction': task.natural_language_instruction,
                'is_active': task.is_active,
            },
            "message": f"Task '{data['name']}' created successfully"
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@require_auth
def update_task(task_id):
    """
    Update a scheduled task.
    
    Request body can include:
    {
        "name": "new name",
        "instruction": "new schedule instruction",
        "is_active": true,
        "description": "new description"
    }
    """
    try:
        data = request.get_json()
        scheduler = get_task_scheduler()
        
        # If instruction changed, reparse schedule
        if 'instruction' in data:
            schedule_config = parse_natural_language_schedule(data['instruction'])
            data['schedule_config'] = schedule_config
            data['natural_language_instruction'] = data.pop('instruction')
        
        task = scheduler.update_task(task_id, **data)
        
        if not task:
            return jsonify({"success": False, "error": "Task not found"}), 404
        
        return jsonify({
            "success": True,
            "task": {
                'id': task.id,
                'name': task.name,
                'is_active': task.is_active,
            },
            "message": f"Task updated successfully"
        }), 200
    
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@require_auth
def delete_task(task_id):
    """Delete a scheduled task."""
    try:
        scheduler = get_task_scheduler()
        success = scheduler.delete_task(task_id)
        
        if not success:
            return jsonify({"success": False, "error": "Task not found"}), 404
        
        return jsonify({
            "success": True,
            "message": "Task deleted successfully"
        }), 200
    
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route('/tasks/<int:task_id>/enable', methods=['POST'])
@require_auth
def enable_task(task_id):
    """Enable a task."""
    try:
        scheduler = get_task_scheduler()
        success = scheduler.enable_task(task_id)
        
        return jsonify({
            "success": success,
            "message": f"Task {'enabled' if success else 'already enabled'}"
        }), 200 if success else 500
    
    except Exception as e:
        logger.error(f"Error enabling task: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route('/tasks/<int:task_id>/disable', methods=['POST'])
@require_auth
def disable_task(task_id):
    """Disable a task."""
    try:
        scheduler = get_task_scheduler()
        success = scheduler.disable_task(task_id)
        
        return jsonify({
            "success": success,
            "message": f"Task {'disabled' if success else 'already disabled'}"
        }), 200 if success else 500
    
    except Exception as e:
        logger.error(f"Error disabling task: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route('/start', methods=['POST'])
@require_auth
def start_scheduler():
    """Start the task scheduler."""
    try:
        scheduler = get_task_scheduler()
        scheduler.start()
        
        return jsonify({
            "success": True,
            "message": "Task scheduler started"
        }), 200
    
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scheduler_bp.route('/stop', methods=['POST'])
@require_auth
def stop_scheduler():
    """Stop the task scheduler."""
    try:
        scheduler = get_task_scheduler()
        scheduler.stop()
        
        return jsonify({
            "success": True,
            "message": "Task scheduler stopped"
        }), 200
    
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Initialize task handlers
def send_email_smtp(to_address, subject, body, reply_to=None):
    """Send email via SMTP (Gmail, Outlook, etc.)."""
    try:
        email_address = os.getenv('EMAIL_ADDRESS')
        email_password = os.getenv('EMAIL_PASSWORD')
        email_provider = os.getenv('EMAIL_PROVIDER', 'gmail')
        
        # SMTP Configuration for different providers
        smtp_config = {
            'gmail': ('smtp.gmail.com', 587),
            'outlook': ('smtp-mail.outlook.com', 587),
            'yahoo': ('smtp.mail.yahoo.com', 587),
            'icloud': ('smtp.mail.icloud.com', 587),
        }
        
        smtp_server, smtp_port = smtp_config.get(
            email_provider,
            (os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com'),
             int(os.getenv('EMAIL_SMTP_PORT', 587)))
        )
        
        # Determine if using SSL or TLS
        use_ssl = int(smtp_port) == 465 or os.getenv('EMAIL_SMTP_TLS', '').lower() == 'ssl'
        
        # Create MIME message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = email_address
        msg['To'] = to_address
        if reply_to:
            msg['In-Reply-To'] = reply_to
            msg['References'] = reply_to
        
        # Attach HTML body
        msg.attach(MIMEText(body, 'html'))
        
        # Connect and send
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, int(smtp_port))
        else:
            server = smtplib.SMTP(smtp_server, int(smtp_port))
        
        try:
            if not use_ssl:
                server.starttls()
            server.login(email_address, email_password)
            server.send_message(msg)
            logger.info(f"✓ Email sent to {to_address} with subject '{subject}'")
            return True
        finally:
            server.quit()
    
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def initialize_email_handlers(scheduler: TaskScheduler):
    """Register email-related task handlers."""
    
    def handle_email_check(task, task_config):
        """Handle email check task."""
        email_service = EmailConfig.get_email_service()
        if not email_service:
            logger.warning("Email service not configured, skipping email check")
            return None
        
        emails = email_service.get_unread_emails(limit=task_config.get('limit', 10))
        email_service.disconnect()
        
        logger.info(f"✓ Email check completed: {len(emails)} unread emails")
        return {"emails_checked": len(emails), "unread_count": len(emails)}
    
    def handle_email_respond(task, task_config):
        """Handle automatic email response with LLM."""
        try:
            email_service = EmailConfig.get_email_service()
            if not email_service:
                logger.warning("Email service not configured")
                return {"status": "error", "message": "Email service not configured"}
            
            # Get unread emails
            emails = email_service.get_unread_emails(limit=task_config.get('limit', 5))
            email_service.disconnect()
            
            if not emails:
                logger.info("No unread emails to respond to")
                return {"status": "success", "responded_count": 0, "message": "No emails to respond to"}
            
            # Get LLM client
            llm = build_llm()
            if not llm:
                logger.warning("LLM not configured, cannot generate responses")
                return {"status": "error", "message": "LLM not configured"}
            
            responded_count = 0
            failed_count = 0
            responses = []
            
            for email in emails:
                try:
                    # Generate response using LLM
                    prompt = f"""You are a professional email assistant. 
                    
The user received this email:

From: {email.get('from', 'Unknown')}
Subject: {email.get('subject', '(no subject)')}

Body:
{email.get('text', email.get('html', '(no body)'))}

Please generate a professional, concise response email. 
Keep it brief (2-3 sentences), professional, and helpful.
Only return the email body, no subject line or formatting."""
                    
                    messages = [{"role": "user", "content": prompt}]
                    response_text = llm.chat(messages)
                    
                    if response_text:
                        # Generate subject for reply
                        subject = f"Re: {email.get('subject', 'Your inquiry')}"
                        
                        # Send email
                        if send_email_smtp(
                            email.get('from'),
                            subject,
                            response_text,
                            reply_to=email.get('id')
                        ):
                            responded_count += 1
                            responses.append({
                                "to": email.get('from'),
                                "subject": subject,
                                "status": "sent"
                            })
                            logger.info(f"✓ Auto-response sent to {email.get('from')}")
                        else:
                            failed_count += 1
                            responses.append({
                                "to": email.get('from'),
                                "status": "failed",
                                "error": "SMTP send failed"
                            })
                    else:
                        failed_count += 1
                        responses.append({
                            "to": email.get('from'),
                            "status": "failed",
                            "error": "LLM response generation failed"
                        })
                
                except Exception as e:
                    logger.error(f"Error processing email from {email.get('from')}: {e}")
                    failed_count += 1
                    responses.append({
                        "to": email.get('from'),
                        "status": "failed",
                        "error": str(e)
                    })
            
            return {
                "status": "success",
                "responded_count": responded_count,
                "failed_count": failed_count,
                "total_processed": len(emails),
                "responses": responses
            }
        
        except Exception as e:
            logger.error(f"Error in email respond task: {e}")
            return {"status": "error", "message": str(e)}
    
    # Register handlers
    scheduler.register_task_handler('email_check', handle_email_check)
    scheduler.register_task_handler('email_respond', handle_email_respond)
