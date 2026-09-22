"""Real-time WebSocket events for email and social media messages."""
import logging
from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Store connected clients
connected_clients = {}


def init_socketio(app):
    """Initialize SocketIO with Flask app."""
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='threading',
        logger=True,
        engineio_logger=True
    )
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        client_id = request.sid
        connected_clients[client_id] = {
            'connected_at': datetime.utcnow().isoformat(),
            'subscriptions': set()
        }
        logger.info(f"✓ Client connected: {client_id} (Total: {len(connected_clients)})")
        emit('connected', {
            'data': 'Connected to Brainr real-time service',
            'client_id': client_id,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        client_id = request.sid
        if client_id in connected_clients:
            del connected_clients[client_id]
        logger.info(f"✓ Client disconnected: {client_id} (Total: {len(connected_clients)})")
    
    @socketio.on('subscribe_emails')
    def handle_subscribe_emails():
        """Subscribe to email updates."""
        client_id = request.sid
        if client_id in connected_clients:
            connected_clients[client_id]['subscriptions'].add('emails')
            logger.info(f"✓ Client subscribed to emails: {client_id}")
            emit('subscribed', {
                'channel': 'emails',
                'message': 'You are now listening for email updates'
            })
    
    @socketio.on('subscribe_whatsapp')
    def handle_subscribe_whatsapp():
        """Subscribe to WhatsApp updates."""
        client_id = request.sid
        if client_id in connected_clients:
            connected_clients[client_id]['subscriptions'].add('whatsapp')
            logger.info(f"✓ Client subscribed to WhatsApp: {client_id}")
            emit('subscribed', {
                'channel': 'whatsapp',
                'message': 'You are now listening for WhatsApp updates'
            })
    
    @socketio.on('subscribe_social_media')
    def handle_subscribe_social_media():
        """Subscribe to all social media updates."""
        client_id = request.sid
        if client_id in connected_clients:
            connected_clients[client_id]['subscriptions'].add('social_media')
            logger.info(f"✓ Client subscribed to social media: {client_id}")
            emit('subscribed', {
                'channel': 'social_media',
                'message': 'You are now listening for all social media updates'
            })
    
    @socketio.on('unsubscribe_emails')
    def handle_unsubscribe_emails():
        """Unsubscribe from email updates."""
        client_id = request.sid
        if client_id in connected_clients:
            connected_clients[client_id]['subscriptions'].discard('emails')
            logger.info(f"✓ Client unsubscribed from emails: {client_id}")
            emit('unsubscribed', {'channel': 'emails'})
    
    @socketio.on('unsubscribe_whatsapp')
    def handle_unsubscribe_whatsapp():
        """Unsubscribe from WhatsApp updates."""
        client_id = request.sid
        if client_id in connected_clients:
            connected_clients[client_id]['subscriptions'].discard('whatsapp')
            logger.info(f"✓ Client unsubscribed from WhatsApp: {client_id}")
            emit('unsubscribed', {'channel': 'whatsapp'})
    
    @socketio.on('unsubscribe_social_media')
    def handle_unsubscribe_social_media():
        """Unsubscribe from social media updates."""
        client_id = request.sid
        if client_id in connected_clients:
            connected_clients[client_id]['subscriptions'].discard('social_media')
            logger.info(f"✓ Client unsubscribed from social media: {client_id}")
            emit('unsubscribed', {'channel': 'social_media'})
    
    @socketio.on('ping')
    def handle_ping():
        """Handle ping - respond with pong."""
        emit('pong', {
            'timestamp': datetime.utcnow().isoformat(),
            'connected_clients': len(connected_clients)
        })
    
    return socketio


def broadcast_email_event(event_type, email_data):
    """
    Broadcast email event to all subscribed clients.
    
    Args:
        event_type: Type of event ('new_email', 'email_received', 'email_stored')
        email_data: Email data dictionary
    """
    try:
        socketio = SocketIO()
        recipients = [
            client_id for client_id, client_info in connected_clients.items()
            if 'emails' in client_info['subscriptions']
        ]
        
        if recipients:
            logger.info(f"Broadcasting email event to {len(recipients)} clients: {event_type}")
            socketio.emit(
                'email_update',
                {
                    'event_type': event_type,
                    'email': email_data,
                    'timestamp': datetime.utcnow().isoformat(),
                    'recipients': len(recipients)
                },
                room=recipients,
                skip_sid=None
            )
        else:
            logger.debug(f"No clients subscribed to email updates (event: {event_type})")
    
    except Exception as e:
        logger.error(f"Error broadcasting email event: {e}", exc_info=True)


def broadcast_whatsapp_event(event_type, message_data):
    """
    Broadcast WhatsApp event to all subscribed clients.
    
    Args:
        event_type: Type of event ('new_message', 'message_received', 'response_sent')
        message_data: Message data dictionary
    """
    try:
        socketio = SocketIO()
        recipients = [
            client_id for client_id, client_info in connected_clients.items()
            if 'whatsapp' in client_info['subscriptions'] or 'social_media' in client_info['subscriptions']
        ]
        
        if recipients:
            logger.info(f"Broadcasting WhatsApp event to {len(recipients)} clients: {event_type}")
            socketio.emit(
                'whatsapp_update',
                {
                    'event_type': event_type,
                    'message': message_data,
                    'timestamp': datetime.utcnow().isoformat(),
                    'recipients': len(recipients)
                },
                room=recipients,
                skip_sid=None
            )
        else:
            logger.debug(f"No clients subscribed to WhatsApp updates (event: {event_type})")
    
    except Exception as e:
        logger.error(f"Error broadcasting WhatsApp event: {e}", exc_info=True)


def broadcast_social_media_event(event_type, channel_type, message_data):
    """
    Broadcast social media event to all subscribed clients.
    
    Args:
        event_type: Type of event ('new_message', 'response_sent', 'error')
        channel_type: Channel type (whatsapp, telegram, etc.)
        message_data: Message data dictionary
    """
    try:
        socketio = SocketIO()
        recipients = [
            client_id for client_id, client_info in connected_clients.items()
            if 'social_media' in client_info['subscriptions']
        ]
        
        if recipients:
            logger.info(f"Broadcasting {channel_type} event to {len(recipients)} clients: {event_type}")
            socketio.emit(
                'social_media_update',
                {
                    'event_type': event_type,
                    'channel': channel_type,
                    'message': message_data,
                    'timestamp': datetime.utcnow().isoformat(),
                    'recipients': len(recipients)
                },
                room=recipients,
                skip_sid=None
            )
        else:
            logger.debug(f"No clients subscribed to social media updates (event: {event_type})")
    
    except Exception as e:
        logger.error(f"Error broadcasting social media event: {e}", exc_info=True)


def get_connected_clients_count():
    """Get number of connected clients."""
    return len(connected_clients)


def get_subscribed_clients(channel):
    """Get clients subscribed to a specific channel."""
    return [
        client_id for client_id, client_info in connected_clients.items()
        if channel in client_info['subscriptions']
    ]
