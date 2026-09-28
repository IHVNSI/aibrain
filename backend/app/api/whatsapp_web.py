"""API endpoints for WhatsApp Web login and messaging."""
import logging
import os
from flask import Blueprint, request, jsonify
from ..whatsapp_service import WhatsAppManager

logger = logging.getLogger(__name__)

whatsapp_web_bp = Blueprint('whatsapp_web', __name__, url_prefix='/api/whatsapp')


@whatsapp_web_bp.route('/login', methods=['POST'])
def login_whatsapp():
    """
    Start WhatsApp Web login with QR code (non-blocking).
    Automatically connects if already logged in.
    Displays QR code in terminal and browser.
    
    Request body:
    {
        "session_name": "default",  (optional)
        "print_terminal": true      (optional - print QR to terminal)
    }
    
    Response:
    {
        "success": true,
        "message": "QR code ready - Please scan with your phone",
        "qr_code": "data:image/png;base64,...",
        "polling_url": "/api/whatsapp/status",
        "session_name": "default",
        "logged_in": false (or true if already logged in)
    }
    """
    try:
        # Handle requests without Content-Type header
        data = request.get_json(silent=True) or {}
        session_name = data.get('session_name', 'default')
        
        # Get WhatsApp instance
        wa = WhatsAppManager.get_instance(session_name)
        
        # Start non-blocking login (handles existing sessions automatically)
        logger.info(f"Starting WhatsApp Web login for session: {session_name}")
        result = wa.start_login_async()
        
        # Add session name to result
        result['session_name'] = session_name
        
        # If success and has QR code, print to terminal
        if result.get('success') and result.get('qr_code'):
            logger.info("📱 QR code captured - Printing to terminal...")
            # Note: start_login_async now calls print_qr_to_terminal internally
        
        # Return 200 for all successful outcomes (including already logged in)
        if result.get('success'):
            return jsonify(result), 200
        else:
            # Return 400 for actual errors
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"WhatsApp login error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@whatsapp_web_bp.route('/status', methods=['GET'])
def whatsapp_status():
    """
    Check WhatsApp login status.
    
    Query params:
    - session_name: Session name (default: "default")
    
    Response:
    {
        "logged_in": true,
        "session_name": "default",
        "timestamp": "2024-09-22T10:30:00Z"
    }
    """
    try:
        session_name = request.args.get('session_name', 'default')
        wa = WhatsAppManager.get_instance(session_name)
        
        return jsonify({
            "logged_in": wa.is_logged_in,
            "session_name": session_name,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@whatsapp_web_bp.route('/send', methods=['POST'])
def send_message():
    """
    Send WhatsApp message.
    
    Request body:
    {
        "phone_number": "+1234567890",
        "message": "Hello, how are you?",
        "session_name": "default"  (optional)
    }
    
    Response:
    {
        "success": true,
        "message": "Message sent",
        "phone_number": "+1234567890"
    }
    """
    try:
        data = request.json or {}
        phone_number = data.get('phone_number', '')
        message_text = data.get('message', '')
        session_name = data.get('session_name', 'default')
        
        if not phone_number or not message_text:
            return jsonify({
                "success": False,
                "error": "Missing phone_number or message"
            }), 400
        
        # Get WhatsApp instance
        wa = WhatsAppManager.get_instance(session_name)
        
        if not wa.is_logged_in:
            return jsonify({
                "success": False,
                "error": "Not logged in to WhatsApp",
                "message": "Please login first using /api/whatsapp/login"
            }), 401
        
        # Send message
        success = wa.send_message(phone_number, message_text)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Message sent",
                "phone_number": phone_number
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Failed to send message"
            }), 400
    
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@whatsapp_web_bp.route('/chats', methods=['GET'])
def get_chats():
    """
    Get list of recent chats.
    
    Query params:
    - session_name: Session name (default: "default")
    - limit: Number of chats (default: 10)
    
    Response:
    {
        "success": true,
        "chats": [
            {"name": "Friend Name"},
            {"name": "Mom"}
        ]
    }
    """
    try:
        session_name = request.args.get('session_name', 'default')
        limit = int(request.args.get('limit', 10))
        
        wa = WhatsAppManager.get_instance(session_name)
        
        if not wa.is_logged_in:
            return jsonify({
                "success": False,
                "error": "Not logged in to WhatsApp"
            }), 401
        
        chats = wa.get_chats(limit=limit)
        
        return jsonify({
            "success": True,
            "chats": chats
        }), 200
    
    except Exception as e:
        logger.error(f"Get chats error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@whatsapp_web_bp.route('/messages', methods=['POST'])
def get_messages():
    """
    Get messages from a specific chat.
    
    Request body:
    {
        "chat_name": "Friend Name",
        "limit": 20,
        "session_name": "default"  (optional)
    }
    
    Response:
    {
        "success": true,
        "chat_name": "Friend Name",
        "messages": [
            {"text": "Hi", "time": "1234567890", "incoming": true},
            {"text": "Hello!", "time": "1234567891", "incoming": false}
        ]
    }
    """
    try:
        data = request.json or {}
        chat_name = data.get('chat_name', '')
        limit = int(data.get('limit', 20))
        session_name = data.get('session_name', 'default')
        
        if not chat_name:
            return jsonify({
                "success": False,
                "error": "Missing chat_name"
            }), 400
        
        wa = WhatsAppManager.get_instance(session_name)
        
        if not wa.is_logged_in:
            return jsonify({
                "success": False,
                "error": "Not logged in to WhatsApp"
            }), 401
        
        messages = wa.get_messages(chat_name, limit=limit)
        
        return jsonify({
            "success": True,
            "chat_name": chat_name,
            "messages": messages
        }), 200
    
    except Exception as e:
        logger.error(f"Get messages error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@whatsapp_web_bp.route('/logout', methods=['POST'])
def logout_whatsapp():
    """
    Logout from WhatsApp Web.
    
    Request body:
    {
        "session_name": "default"  (optional)
    }
    
    Response:
    {
        "success": true,
        "message": "Logged out"
    }
    """
    try:
        # Handle requests without Content-Type header
        data = request.get_json(silent=True) or {}
        session_name = data.get('session_name', 'default')
        
        wa = WhatsAppManager.get_instance(session_name)
        wa.close()
        
        return jsonify({
            "success": True,
            "message": "Logged out from WhatsApp Web"
        }), 200
    
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@whatsapp_web_bp.route('/handle-message', methods=['POST'])
def handle_message_ai():
    """
    Handle incoming message with AI processing.
    Routes message to AI and generates intelligent response.
    
    Request body:
    {
        "message": "What are your business hours?",
        "sender_name": "John Doe",  (optional)
        "session_name": "default"   (optional)
    }
    
    Response:
    {
        "success": true,
        "response": "Our business hours are 9AM-6PM, Monday to Friday.",
        "ready_to_send": true,
        "from_sender": "John Doe"
    }
    """
    try:
        data = request.json or {}
        message_text = data.get('message', '')
        sender_name = data.get('sender_name', 'User')
        session_name = data.get('session_name', 'default')
        
        if not message_text:
            return jsonify({
                "success": False,
                "error": "Missing message text"
            }), 400
        
        # Get WhatsApp instance
        wa = WhatsAppManager.get_instance(session_name)
        
        if not wa.is_logged_in:
            return jsonify({
                "success": False,
                "error": "Not logged in to WhatsApp"
            }), 401
        
        # Process message with AI
        logger.info(f"Processing WhatsApp message from {sender_name}: {message_text[:50]}...")
        result = wa.handle_message_with_ai(message_text, sender_name)
        
        return jsonify(result), 200 if result.get('success') else 400
    
    except Exception as e:
        logger.error(f"Handle message error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@whatsapp_web_bp.route('/incoming-messages', methods=['GET'])
def get_incoming_messages_api():
    """
    Get incoming/new messages from WhatsApp.
    
    Query params:
    - session_name: Session name (default: "default")
    - chat_name: Specific chat name (optional, gets all if not specified)
    
    Response:
    {
        "success": true,
        "messages": [
            {
                "text": "Hi, how are you?",
                "time": "1234567890",
                "incoming": true,
                "from": "John Doe"
            }
        ],
        "count": 1
    }
    """
    try:
        session_name = request.args.get('session_name', 'default')
        chat_name = request.args.get('chat_name', None)
        
        wa = WhatsAppManager.get_instance(session_name)
        
        if not wa.is_logged_in:
            return jsonify({
                "success": False,
                "error": "Not logged in to WhatsApp"
            }), 401
        
        messages = wa.get_incoming_messages(chat_name)
        
        return jsonify({
            "success": True,
            "messages": messages,
            "count": len(messages)
        }), 200
    
    except Exception as e:
        logger.error(f"Get incoming messages error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@whatsapp_web_bp.route('/send-ai-response', methods=['POST'])
def send_ai_response():
    """
    Send AI-generated response to WhatsApp contact.
    
    Request body:
    {
        "phone_number": "+1234567890",
        "message": "Thank you for your message...",
        "session_name": "default"  (optional)
    }
    
    Response:
    {
        "success": true,
        "message": "AI response sent to WhatsApp",
        "phone_number": "+1234567890"
    }
    """
    try:
        data = request.json or {}
        phone_number = data.get('phone_number', '')
        message_text = data.get('message', '')
        session_name = data.get('session_name', 'default')
        
        if not phone_number or not message_text:
            return jsonify({
                "success": False,
                "error": "Missing phone_number or message"
            }), 400
        
        # Get WhatsApp instance
        wa = WhatsAppManager.get_instance(session_name)
        
        if not wa.is_logged_in:
            return jsonify({
                "success": False,
                "error": "Not logged in to WhatsApp"
            }), 401
        
        # Send message
        logger.info(f"Sending AI response to {phone_number}")
        success = wa.send_message(phone_number, message_text)
        
        if success:
            return jsonify({
                "success": True,
                "message": "AI response sent to WhatsApp",
                "phone_number": phone_number
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Failed to send AI response"
            }), 400
    
    except Exception as e:
        logger.error(f"Send AI response error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@whatsapp_web_bp.route('/processed-responses', methods=['GET'])
def get_processed_responses():
    """
    Get AI responses generated from listened/received WhatsApp messages.
    Messages are automatically listened to after login and processed as AI prompts.
    
    Query params:
    - session_name: Session name (default: "default")
    - limit: Max responses to return (default: 20)
    
    Response:
    {
        "success": true,
        "responses": [
            {
                "from": "John Doe",
                "received_message": "What are your prices?",
                "ai_response": "Our prices range from $50-$500...",
                "timestamp": "2024-09-22T10:30:00",
                "ready_to_send": true
            }
        ],
        "count": 1
    }
    """
    try:
        session_name = request.args.get('session_name', 'default')
        limit = int(request.args.get('limit', 20))
        
        wa = WhatsAppManager.get_instance(session_name)
        
        if not wa.is_logged_in:
            return jsonify({
                "success": False,
                "error": "Not logged in to WhatsApp"
            }), 401
        
        # Get processed responses
        all_responses = wa.get_ai_processed_responses()
        responses = all_responses[:limit]
        
        return jsonify({
            "success": True,
            "responses": responses,
            "count": len(responses),
            "total_queued": len(all_responses),
            "listener_active": wa.listener_active
        }), 200
    
    except Exception as e:
        logger.error(f"Get processed responses error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@whatsapp_web_bp.route('/processed-responses', methods=['DELETE'])
def clear_processed_responses():
    """
    Clear the queue of processed AI responses.
    
    Query params:
    - session_name: Session name (default: "default")
    
    Response:
    {
        "success": true,
        "message": "Cleared 3 processed responses",
        "cleared_count": 3
    }
    """
    try:
        session_name = request.args.get('session_name', 'default')
        
        wa = WhatsAppManager.get_instance(session_name)
        
        if not wa.is_logged_in:
            return jsonify({
                "success": False,
                "error": "Not logged in to WhatsApp"
            }), 401
        
        cleared_count = wa.clear_processed_responses()
        
        return jsonify({
            "success": True,
            "message": f"Cleared {cleared_count} processed responses",
            "cleared_count": cleared_count
        }), 200
    
    except Exception as e:
        logger.error(f"Clear processed responses error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Import at module level for reference
from datetime import datetime
