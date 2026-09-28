"""Social media channel integration endpoints (WhatsApp, Telegram, etc.)."""
import logging
import json
from flask import Blueprint, request, jsonify
from datetime import datetime
from ..extensions import db
from ..auth import require_auth
from ..models import SocialMediaAccount, SocialMediaMessage, SocialMediaResponse, AIContext, TrainingItem, SecuritySetting
from ..llm.factory import build_llm

logger = logging.getLogger(__name__)

social_media_bp = Blueprint('social_media', __name__, url_prefix='/api/social-media')


# ============================================================================
# ACCOUNT MANAGEMENT
# ============================================================================

@social_media_bp.route('/accounts', methods=['GET'])
@require_auth
def get_accounts():
    """Get all configured social media accounts."""
    try:
        accounts = SocialMediaAccount.query.all()
        return jsonify({
            "success": True,
            "accounts": [a.to_dict() for a in accounts]
        }), 200
    except Exception as e:
        logger.error(f"Error getting accounts: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@social_media_bp.route('/accounts', methods=['POST'])
@require_auth
def create_account():
    """
    Create or update a social media account.
    
    Request body:
    {
        "channel_type": "whatsapp",  // or telegram, signal, etc.
        "account_id": "+1234567890",  // Phone number for WhatsApp
        "account_name": "Support Line",
        "api_key": "your_api_key",
        "owner_number": "+9876543210",  // Only respond to this number
        "auto_response_enabled": false,
        "treat_as_prompt": true,
        "use_context": true,
        "use_security_policies": true,
        "ai_instructions": "Be helpful and professional"
    }
    """
    try:
        data = request.json or {}
        
        channel_type = data.get('channel_type', '').lower()
        account_id = data.get('account_id', '').strip()
        account_name = data.get('account_name', '').strip()
        api_key = data.get('api_key', '').strip()
        owner_number = data.get('owner_number', '').strip()
        
        # Validate required fields
        if not channel_type or not account_id or not api_key:
            return jsonify({"success": False, "error": "channel_type, account_id, and api_key are required"}), 400
        
        # Check if account already exists
        existing = SocialMediaAccount.query.filter_by(
            channel_type=channel_type,
            account_id=account_id
        ).first()
        
        if existing:
            # Update existing
            existing.account_name = account_name or existing.account_name
            existing.api_key = api_key
            existing.owner_number = owner_number or existing.owner_number
            existing.auto_response_enabled = data.get('auto_response_enabled', existing.auto_response_enabled)
            existing.treat_as_prompt = data.get('treat_as_prompt', existing.treat_as_prompt)
            existing.use_context = data.get('use_context', existing.use_context)
            existing.use_security_policies = data.get('use_security_policies', existing.use_security_policies)
            existing.ai_instructions = data.get('ai_instructions', existing.ai_instructions)
            existing.enabled = data.get('enabled', existing.enabled)
            db.session.commit()
            return jsonify({
                "success": True,
                "message": "Account updated successfully",
                "account": existing.to_dict()
            }), 200
        else:
            # Create new
            account = SocialMediaAccount(
                channel_type=channel_type,
                account_id=account_id,
                account_name=account_name,
                api_key=api_key,
                owner_number=owner_number,
                auto_response_enabled=data.get('auto_response_enabled', False),
                treat_as_prompt=data.get('treat_as_prompt', True),
                use_context=data.get('use_context', True),
                use_security_policies=data.get('use_security_policies', True),
                ai_instructions=data.get('ai_instructions', ''),
                enabled=data.get('enabled', True)
            )
            db.session.add(account)
            db.session.commit()
            
            logger.info(f"Created {channel_type} account: {account_id}")
            
            return jsonify({
                "success": True,
                "message": f"{channel_type.upper()} account configured successfully",
                "account": account.to_dict()
            }), 201
    
    except Exception as e:
        logger.error(f"Error creating account: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@social_media_bp.route('/accounts/<int:account_id>', methods=['DELETE'])
@require_auth
def delete_account(account_id):
    """Delete a social media account."""
    try:
        account = SocialMediaAccount.query.get(account_id)
        if not account:
            return jsonify({"success": False, "error": "Account not found"}), 404
        
        db.session.delete(account)
        db.session.commit()
        
        logger.info(f"Deleted account: {account.channel_type} {account.account_id}")
        
        return jsonify({"success": True, "message": "Account deleted successfully"}), 200
    
    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# MESSAGE HANDLING - INCOMING MESSAGES
# ============================================================================

@social_media_bp.route('/webhook/message', methods=['POST'])
def receive_message():
    """
    Webhook endpoint for receiving messages from social media platforms.
    Broadcasts real-time updates to WebSocket clients.
    
    Request body (WhatsApp example):
    {
        "channel": "whatsapp",
        "account_id": "+1234567890",
        "sender_id": "+9876543210",
        "sender_name": "John",
        "message_id": "unique_message_id",
        "message": "Hello, what is the status?",
        "timestamp": "2024-09-22T10:30:00Z"
    }
    """
    try:
        from ..socket_events import broadcast_social_media_event
        
        data = request.json or {}
        
        channel = data.get('channel', '').lower()
        account_id = data.get('account_id', '')
        sender_id = data.get('sender_id', '')
        message_text = data.get('message', '')
        message_id = data.get('message_id', '')
        timestamp = data.get('timestamp', datetime.utcnow().isoformat())
        sender_name = data.get('sender_name', 'Unknown')
        
        # Validate
        if not channel or not account_id or not sender_id or not message_text:
            return jsonify({"success": False, "error": "Missing required fields"}), 400
        
        # Find the account
        account = SocialMediaAccount.query.filter_by(
            channel_type=channel,
            account_id=account_id,
            enabled=True
        ).first()
        
        if not account:
            logger.warning(f"Received message for unconfigured account: {channel} {account_id}")
            return jsonify({"success": False, "error": "Account not configured"}), 404
        
        # Check if message is from owner
        is_owner = sender_id == account.owner_number if account.owner_number else False
        
        # Save incoming message
        msg = SocialMediaMessage(
            account_id=account.id,
            channel_type=channel,
            sender_id=sender_id,
            sender_name=sender_name,
            message_text=message_text,
            message_id=message_id,
            received_at=datetime.fromisoformat(timestamp.replace('Z', '+00:00')) if isinstance(timestamp, str) else timestamp,
            is_owner_message=is_owner
        )
        db.session.add(msg)
        db.session.commit()
        
        logger.info(f"Received {channel} message from {sender_id}: {message_text[:50]}")
        
        # Broadcast incoming message to WebSocket clients
        broadcast_social_media_event('new_message', channel, {
            'message_id': msg.id,
            'sender_id': sender_id,
            'sender_name': sender_name,
            'message': message_text,
            'account': account.account_name,
            'is_owner': is_owner,
            'timestamp': msg.received_at.isoformat()
        })
        
        # Process message if enabled and from owner
        if account.treat_as_prompt and is_owner:
            # Generate AI response
            try:
                response_text = generate_response(account, msg)
                if response_text:
                    msg.is_processed = True
                    db.session.commit()
                    
                    logger.info(f"Generated response for message {message_id}")
                    
                    # Broadcast response to WebSocket clients
                    broadcast_social_media_event('response_sent', channel, {
                        'message_id': msg.id,
                        'sender_id': sender_id,
                        'response': response_text,
                        'account': account.account_name,
                        'timestamp': datetime.utcnow().isoformat()
                    })
                    
                    # In production, send response back via WhatsApp API
                    return jsonify({
                        "success": True,
                        "message": "Message received and processed",
                        "response": response_text
                    }), 200
            except Exception as e:
                logger.error(f"Error generating response: {e}")
                broadcast_social_media_event('error', channel, {
                    'message_id': msg.id,
                    'error': f"Failed to generate response: {str(e)}"
                })
        
        return jsonify({
            "success": True,
            "message": "Message received",
            "message_id": msg.id
        }), 200
    
    except Exception as e:
        logger.error(f"Error receiving message: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# MESSAGE PROCESSING - GENERATE AI RESPONSES
# ============================================================================

def generate_response(account: SocialMediaAccount, msg: SocialMediaMessage) -> str:
    """
    Generate AI response for incoming social media message.
    Uses full context like email auto-reply: training data, security policies, system context.
    """
    try:
        # Get LLM
        llm = build_llm()
        if not llm:
            logger.error("LLM not configured")
            return None
        
        # Get full system context
        ai_context = AIContext.get_active()
        system_instructions = ""
        
        if ai_context:
            system_instructions = ai_context.system_instructions or ""
        else:
            system_instructions = "You are a helpful and professional assistant. Respond to the user's request."
        
        # Build context
        training_context = ""
        if account.use_context:
            training_items = TrainingItem.query.limit(10).all()
            if training_items:
                training_context = "\n\nAvailable Context from Training Data:"
                for item in training_items:
                    if item.metadata and 'description' in item.metadata:
                        training_context += f"\n- {item.metadata['description']}"
        
        # Get security policies
        security_context = ""
        if account.use_security_policies:
            security_settings = SecuritySetting.query.first()
            if security_settings and security_settings.sql_banned_keywords:
                security_context = f"\n\nSecurity & Policy Guidelines to follow:\n- Banned SQL keywords: {security_settings.sql_banned_keywords}"
        
        # Build prompt
        prompt = f"""You are assisting via {account.channel_type.upper()} ({account.account_name}).

Incoming message from {msg.sender_name} ({msg.sender_id}):
"{msg.message_text}"

{account.ai_instructions or "Respond professionally and helpfully."}

{training_context}

{security_context}

Please provide a concise, helpful response (2-3 sentences for WhatsApp). Keep it brief and direct."""
        
        # Generate response
        messages = [{"role": "user", "content": prompt}]
        response_text = llm.chat(messages)
        
        if response_text:
            # Save response to database
            response = SocialMediaResponse(
                message_id=msg.id,
                account_id=account.id,
                response_text=response_text,
                ai_generated=True,
                prompt_used=prompt,
                context_used=json.dumps({
                    "system_instructions": system_instructions[:200],
                    "training_context": bool(training_context),
                    "security_context": bool(security_context)
                })
            )
            db.session.add(response)
            db.session.commit()
            
            logger.info(f"Generated response for message {msg.id}")
            return response_text
        
        return None
    
    except Exception as e:
        logger.error(f"Error in generate_response: {e}")
        return None


# ============================================================================
# MESSAGE HISTORY
# ============================================================================

@social_media_bp.route('/accounts/<int:account_id>/messages', methods=['GET'])
@require_auth
def get_messages(account_id):
    """Get messages for an account with pagination."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        account = SocialMediaAccount.query.get(account_id)
        if not account:
            return jsonify({"success": False, "error": "Account not found"}), 404
        
        paginated = SocialMediaMessage.query.filter_by(account_id=account_id).order_by(
            SocialMediaMessage.received_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            "success": True,
            "messages": [m.to_dict() for m in paginated.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": paginated.total,
                "total_pages": paginated.pages
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@social_media_bp.route('/accounts/<int:account_id>/responses', methods=['GET'])
@require_auth
def get_responses(account_id):
    """Get responses sent from an account."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        account = SocialMediaAccount.query.get(account_id)
        if not account:
            return jsonify({"success": False, "error": "Account not found"}), 404
        
        paginated = SocialMediaResponse.query.filter_by(account_id=account_id).order_by(
            SocialMediaResponse.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            "success": True,
            "responses": [r.to_dict() for r in paginated.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": paginated.total,
                "total_pages": paginated.pages
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting responses: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
