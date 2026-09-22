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
    Start WhatsApp Web login with QR code.
    
    Request body:
    {
        "session_name": "default"  (optional)
    }
    
    Response:
    {
        "success": true,
        "message": "QR code displayed - please scan",
        "qr_code": "/path/to/qr.png",
        "session_name": "default"
    }
    """
    try:
        data = request.json or {}
        session_name = data.get('session_name', 'default')
        
        # Get WhatsApp instance
        wa = WhatsAppManager.get_instance(session_name)
        
        # Start login
        logger.info(f"Starting WhatsApp Web login for session: {session_name}")
        success = wa.login()
        
        if success:
            return jsonify({
                "success": True,
                "message": "✓ Logged in to WhatsApp Web",
                "session_name": session_name
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Failed to login - please try again",
                "session_name": session_name
            }), 400
    
    except Exception as e:
        logger.error(f"WhatsApp login error: {e}")
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
        data = request.json or {}
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


# Import at module level for reference
from datetime import datetime
