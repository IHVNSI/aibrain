"""Additional email endpoints: auto-reply, drafts, and send"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Blueprint, request, jsonify
from datetime import datetime
import os
import json

from ..extensions import db
from ..auth import require_auth
from ..models import DraftEmail, AutoReplySettings, StoredEmail, SentEmail
from ..email_service import EmailConfig
from ..llm.factory import build_llm

logger = logging.getLogger(__name__)

# Create blueprint
extra_email_bp = Blueprint('extra_email', __name__, url_prefix='/api/email')


# ============================================================================
# AUTO-REPLY ENDPOINTS
# ============================================================================

@extra_email_bp.route('/auto-reply/settings', methods=['GET'])
@require_auth
def get_auto_reply_settings():
    """Get auto-reply configuration."""
    try:
        settings = AutoReplySettings.query.first()
        if not settings:
            # Create default settings if none exist
            settings = AutoReplySettings(
                enabled=False,
                mode='review',
                ai_instructions='Be professional and concise in your response.',
                use_database=True,
                enabled_folders='INBOX'
            )
            db.session.add(settings)
            db.session.commit()
        
        return jsonify({
            "success": True,
            "settings": settings.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting auto-reply settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@extra_email_bp.route('/auto-reply/settings', methods=['POST'])
@require_auth
def update_auto_reply_settings():
    """Update auto-reply configuration."""
    try:
        data = request.json or {}
        
        settings = AutoReplySettings.query.first()
        if not settings:
            settings = AutoReplySettings()
        
        # Update fields
        if 'enabled' in data:
            settings.enabled = data['enabled']
        if 'mode' in data:
            settings.mode = data['mode']  # 'auto' or 'review'
        if 'ai_instructions' in data:
            settings.ai_instructions = data['ai_instructions']
        if 'use_database' in data:
            settings.use_database = data['use_database']
        if 'database_context' in data:
            import json
            settings.database_context = json.dumps(data['database_context'])
        if 'reply_template' in data:
            settings.reply_template = data['reply_template']
        if 'enabled_folders' in data:
            if isinstance(data['enabled_folders'], list):
                settings.enabled_folders = ','.join(data['enabled_folders'])
            else:
                settings.enabled_folders = data['enabled_folders']
        
        db.session.add(settings)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Auto-reply settings updated",
            "settings": settings.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Error updating auto-reply settings: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@extra_email_bp.route('/auto-reply/generate', methods=['POST'])
@require_auth
def generate_auto_reply():
    """
    Generate an auto-reply for a specific email using AI.
    Treats the email like a chat prompt with full system context, training data, and security policies.
    
    Request body:
    {
        "email_id": 123,  // ID of StoredEmail to reply to
        "custom_prompt": "Please mention the project status"
    }
    """
    try:
        data = request.json or {}
        email_id = data.get('email_id')
        custom_prompt = data.get('custom_prompt', '')
        
        if not email_id:
            return jsonify({"success": False, "error": "email_id required"}), 400
        
        # Get the email to reply to
        email = StoredEmail.query.get(email_id)
        if not email:
            return jsonify({"success": False, "error": "Email not found"}), 404
        
        # Check if email is unread - only unread emails can trigger auto-reply
        if email.is_read:
            return jsonify({"success": False, "error": "Only unread emails can trigger auto-reply"}), 400
        
        # Get auto-reply settings
        settings = AutoReplySettings.query.first()
        if not settings or not settings.enabled:
            return jsonify({"success": False, "error": "Auto-reply not enabled"}), 400
        
        # Get LLM
        llm = build_llm()
        if not llm:
            return jsonify({"success": False, "error": "LLM not configured"}), 500
        
        # Get full system context (like chat interface)
        from app.models import AIContext, TrainingItem, SecuritySetting
        
        ai_context = AIContext.get_active()
        system_instructions = ""
        
        if ai_context:
            system_instructions = ai_context.system_prompt or ""
        else:
            system_instructions = """You are a professional and helpful assistant. Respond thoughtfully and accurately to the user's requests."""
        
        # Get training items for context
        training_items = TrainingItem.query.limit(10).all()
        training_context = ""
        if training_items:
            training_context = "\n\nAvailable Context from Training Data:"
            for item in training_items:
                if item.metadata and 'description' in item.metadata:
                    training_context += f"\n- {item.metadata['description']}"
        
        # Get security settings and policies
        security_settings = SecuritySetting.query.filter_by(enabled=True).all()
        security_context = ""
        if security_settings:
            security_context = "\n\nSecurity & Policy Guidelines to follow:"
            for setting in security_settings:
                security_context += f"\n- {setting.name}: {setting.description or 'N/A'}"
        
        # Build database context if enabled
        database_context = ""
        if settings.use_database:
            database_context = "\n\nDatabase Context Available: You have access to relevant business data and historical information. Consider referencing it to provide accurate, informed responses."
        
        # Build comprehensive prompt treating email like chat prompt
        email_prompt = f"""You received this email message that requires a professional response:

From: {email.from_address}
Subject: {email.subject}
Date: {email.received_date.isoformat() if email.received_date else 'N/A'}

Message:
{email.body or email.html_body or '(no content)'}

{f'User Additional Context: {custom_prompt}' if custom_prompt else ''}

{settings.ai_instructions if settings.ai_instructions else ''}

Please generate a professional, helpful reply email. Guidelines:
- Address the sender's points directly
- Be concise (2-3 sentences)
- Maintain a professional tone
- Only output the reply body (no subject, no greeting)"""
        
        # Build messages with full context (like chat interface)
        messages = [
            {"role": "user", "content": email_prompt}
        ]
        
        # Prepare full context for logging/auditing
        full_context = {
            "system_instructions": system_instructions,
            "training_context": training_context,
            "security_context": security_context,
            "database_context": database_context
        }
        
        # Generate response with full LLM context
        response_text = llm.chat(messages)
        
        if not response_text:
            return jsonify({"success": False, "error": "Failed to generate response"}), 500
        
        # Create draft email with AI context
        draft = DraftEmail(
            to_address=email.from_address,
            subject=f"Re: {email.subject}",
            body=response_text,
            status='pending_review' if settings.mode == 'review' else 'draft',
            in_reply_to=email_id,
            auto_generated=True,
            ai_prompt=email_prompt,
            ai_context=json.dumps(full_context) if hasattr(draft, 'ai_context') else None
        )
        db.session.add(draft)
        db.session.commit()
        
        logger.info(f"Auto-reply draft created for email from {email.from_address} with full context")
        
        return jsonify({
            "success": True,
            "message": f"Auto-reply created (status: {draft.status}) with full context guidance",
            "draft": draft.to_dict()
        }), 201
    
    except Exception as e:
        logger.error(f"Error generating auto-reply: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# DRAFT & OUTBOX ENDPOINTS
# ============================================================================

@extra_email_bp.route('/drafts', methods=['GET'])
@require_auth
def get_drafts():
    """Get all draft emails (for outbox)."""
    try:
        status = request.args.get('status', 'draft')  # draft, pending_review, sent, failed
        
        query = DraftEmail.query
        if status:
            query = query.filter_by(status=status)
        
        drafts = query.order_by(DraftEmail.created_at.desc()).all()
        
        return jsonify({
            "success": True,
            "drafts": [d.to_dict() for d in drafts],
            "count": len(drafts)
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting drafts: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@extra_email_bp.route('/drafts', methods=['POST'])
@require_auth
def create_draft():
    """
    Create a new draft email.
    
    Request body:
    {
        "to_address": "recipient@example.com",
        "subject": "Email subject",
        "body": "Email body content",
        "html_body": "<p>HTML content</p>",
        "in_reply_to": 123  // Optional: if replying to StoredEmail
    }
    """
    try:
        data = request.json or {}
        
        # Validate required fields
        required = ['to_address', 'subject', 'body']
        if not all(k in data for k in required):
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {required}"
            }), 400
        
        # Create draft
        draft = DraftEmail(
            to_address=data['to_address'],
            cc_address=data.get('cc_address'),
            bcc_address=data.get('bcc_address'),
            subject=data['subject'],
            body=data['body'],
            html_body=data.get('html_body'),
            in_reply_to=data.get('in_reply_to'),
            status='draft'
        )
        db.session.add(draft)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Draft created",
            "draft": draft.to_dict()
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating draft: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@extra_email_bp.route('/drafts/<int:draft_id>', methods=['PUT'])
@require_auth
def update_draft(draft_id):
    """Update a draft email."""
    try:
        draft = DraftEmail.query.get(draft_id)
        if not draft:
            return jsonify({"success": False, "error": "Draft not found"}), 404
        
        data = request.json or {}
        
        # Update fields
        if 'to_address' in data:
            draft.to_address = data['to_address']
        if 'cc_address' in data:
            draft.cc_address = data['cc_address']
        if 'bcc_address' in data:
            draft.bcc_address = data['bcc_address']
        if 'subject' in data:
            draft.subject = data['subject']
        if 'body' in data:
            draft.body = data['body']
        if 'html_body' in data:
            draft.html_body = data['html_body']
        
        draft.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Draft updated",
            "draft": draft.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Error updating draft: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@extra_email_bp.route('/drafts/<int:draft_id>', methods=['DELETE'])
@require_auth
def delete_draft(draft_id):
    """Delete a draft email."""
    try:
        draft = DraftEmail.query.get(draft_id)
        if not draft:
            return jsonify({"success": False, "error": "Draft not found"}), 404
        
        db.session.delete(draft)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Draft deleted"
        }), 200
    
    except Exception as e:
        logger.error(f"Error deleting draft: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# SEND EMAIL ENDPOINTS
# ============================================================================

def send_email_smtp(to_address, subject, body, cc_address=None, bcc_address=None):
    """Send email via SMTP with optional CC and BCC."""
    try:
        email_address = os.getenv('EMAIL_ADDRESS')
        email_password = os.getenv('EMAIL_PASSWORD')
        email_provider = os.getenv('EMAIL_PROVIDER', 'gmail').lower()
        
        # SMTP Configuration
        smtp_config = {
            'gmail': ('smtp.gmail.com', 587),
            'outlook': ('smtp-mail.outlook.com', 587),
            'yahoo': ('smtp.mail.yahoo.com', 587),
            'icloud': ('smtp.mail.icloud.com', 587),
            'custom': (os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com'), 
                      int(os.getenv('EMAIL_SMTP_PORT', '587')))
        }
        
        smtp_server, smtp_port = smtp_config.get(
            email_provider,
            ('smtp.gmail.com', 587)
        )
        
        # Determine if using SSL
        use_ssl = int(smtp_port) == 465
        
        # Create MIME message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = email_address
        msg['To'] = to_address
        
        # Add CC and BCC headers
        if cc_address:
            msg['Cc'] = cc_address
        if bcc_address:
            msg['Bcc'] = bcc_address
        
        # Attach body as HTML
        msg.attach(MIMEText(body, 'html'))
        
        # Connect and send
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, int(smtp_port))
        else:
            server = smtplib.SMTP(smtp_server, int(smtp_port))
            server.starttls()
        
        try:
            server.login(email_address, email_password)
            # Combine all recipients for sending
            recipients = [to_address]
            if cc_address:
                recipients.extend([e.strip() for e in cc_address.split(',')])
            if bcc_address:
                recipients.extend([e.strip() for e in bcc_address.split(',')])
            server.sendmail(email_address, recipients, msg.as_string())
            logger.info(f"Email sent to {to_address}")
            return True
        finally:
            server.quit()
    
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


@extra_email_bp.route('/send', methods=['POST'])
@require_auth
def send_email():
    """
    Send an email directly.
    
    Request body:
    {
        "to_address": "recipient@example.com",
        "subject": "Subject line",
        "body": "Email body (HTML or plain text)",
        "in_reply_to": 123,  // Optional: StoredEmail ID if replying
        "ai_generated": false  // Optional: whether this was AI-generated
    }
    """
    try:
        data = request.json or {}
        
        # Validate
        required = ['to_address', 'subject', 'body']
        if not all(k in data for k in required):
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {required}"
            }), 400
        
        # Send email
        if send_email_smtp(data['to_address'], data['subject'], data['body'], 
                          cc_address=data.get('cc_address'), 
                          bcc_address=data.get('bcc_address')):
            # Create SentEmail record
            try:
                sent = SentEmail(
                    to_address=data['to_address'],
                    cc_address=data.get('cc_address'),
                    bcc_address=data.get('bcc_address'),
                    subject=data['subject'],
                    body=data['body'],
                    html_body=data.get('html_body'),
                    in_reply_to=data.get('in_reply_to'),
                    ai_generated=data.get('ai_generated', False),
                    status='sent'
                )
                db.session.add(sent)
                db.session.commit()
                logger.info(f"Tracked sent email to {data['to_address']}")
            except Exception as e:
                logger.warning(f"Could not track sent email: {e}")
            
            return jsonify({
                "success": True,
                "message": f"Email sent to {data['to_address']}"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Failed to send email"
            }), 500
    
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@extra_email_bp.route('/drafts/<int:draft_id>/send', methods=['POST'])
@require_auth
def send_draft(draft_id):
    """Send a draft email and track it in sent emails."""
    try:
        draft = DraftEmail.query.get(draft_id)
        if not draft:
            return jsonify({"success": False, "error": "Draft not found"}), 404
        
        # Send the email
        if send_email_smtp(draft.to_address, draft.subject, draft.body or draft.html_body,
                          cc_address=draft.cc_address, bcc_address=draft.bcc_address):
            # Create SentEmail record
            try:
                sent = SentEmail(
                    to_address=draft.to_address,
                    cc_address=draft.cc_address,
                    bcc_address=draft.bcc_address,
                    subject=draft.subject,
                    body=draft.body,
                    html_body=draft.html_body,
                    in_reply_to=draft.in_reply_to,
                    from_draft=draft_id,
                    ai_generated=draft.auto_generated,
                    ai_context=draft.ai_prompt,
                    status='sent'
                )
                db.session.add(sent)
            except Exception as e:
                logger.warning(f"Could not create SentEmail record: {e}")
            
            # Update draft status
            draft.status = 'sent'
            draft.sent_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": f"Email sent to {draft.to_address}",
                "draft": draft.to_dict()
            }), 200
        else:
            # Update draft with error status
            draft.status = 'failed'
            draft.error_message = "Failed to send via SMTP"
            db.session.commit()
            
            return jsonify({
                "success": False,
                "error": "Failed to send email",
                "draft": draft.to_dict()
            }), 500
    
    except Exception as e:
        logger.error(f"Error sending draft: {e}")
        draft = DraftEmail.query.get(draft_id)
        if draft:
            draft.status = 'failed'
            draft.error_message = str(e)
            db.session.commit()
        
        return jsonify({"success": False, "error": str(e)}), 500
