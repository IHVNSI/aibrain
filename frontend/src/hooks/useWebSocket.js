/**
 * useWebSocket Hook - Real-time listening for emails and WhatsApp messages
 * Establishes WebSocket connection and handles incoming events
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import io from 'socket.io-client';
import Swal from 'sweetalert2';

// Create global socket instance (singleton)
let globalSocket = null;

export const useWebSocket = () => {
  const [connected, setConnected] = useState(false);
  const [socketId, setSocketId] = useState(null);
  const [lastEvent, setLastEvent] = useState(null);
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Initialize WebSocket connection
  useEffect(() => {
    if (!globalSocket) {
      const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      
      // Create socket connection
      globalSocket = io(API_URL, {
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: Infinity,
        transports: ['websocket', 'polling'],
        path: '/socket.io/',
        autoConnect: true
      });

      globalSocket.on('connect', () => {
        console.log('✓ WebSocket connected:', globalSocket.id);
        setConnected(true);
        setSocketId(globalSocket.id);
      });

      globalSocket.on('connected', (data) => {
        console.log('✓ Connected to Brainr real-time service:', data);
      });

      globalSocket.on('disconnect', (reason) => {
        console.log('✗ WebSocket disconnected:', reason);
        setConnected(false);
        setSocketId(null);
      });

      globalSocket.on('email_update', (data) => {
        console.log('📧 Email update received:', data);
        setLastEvent({ type: 'email', data });
        
        if (data.event_type === 'new_email') {
          // Show toast notification
          Swal.fire({
            position: 'top-right',
            icon: 'info',
            title: 'New Email',
            text: `From: ${data.email.from}\nSubject: ${data.email.subject}`,
            toast: true,
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true
          });
        }
      });

      globalSocket.on('whatsapp_update', (data) => {
        console.log('💬 WhatsApp update received:', data);
        setLastEvent({ type: 'whatsapp', data });
        
        if (data.event_type === 'new_message') {
          // Show toast notification
          Swal.fire({
            position: 'top-right',
            icon: 'info',
            title: 'WhatsApp Message',
            text: `From: ${data.message.sender_name}\n${data.message.message}`,
            toast: true,
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true
          });
        }
      });

      globalSocket.on('social_media_update', (data) => {
        console.log('🌐 Social media update received:', data);
        setLastEvent({ type: 'social_media', data });
        
        if (data.event_type === 'new_message') {
          // Show toast notification for all social media
          Swal.fire({
            position: 'top-right',
            icon: 'info',
            title: `${data.channel.toUpperCase()} Message`,
            text: `From: ${data.message.sender_name}\n${data.message.message}`,
            toast: true,
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true
          });
        }
      });

      globalSocket.on('subscribed', (data) => {
        console.log('✓ Subscribed to:', data.channel);
      });

      globalSocket.on('unsubscribed', (data) => {
        console.log('✓ Unsubscribed from:', data.channel);
      });

      globalSocket.on('error', (error) => {
        console.error('WebSocket error:', error);
      });

      socketRef.current = globalSocket;
    }

    return () => {
      // Cleanup is handled by global singleton pattern
    };
  }, []);

  // Subscribe to email updates
  const subscribeEmails = useCallback(() => {
    if (globalSocket && globalSocket.connected) {
      globalSocket.emit('subscribe_emails');
      console.log('📧 Subscribed to email updates');
    }
  }, []);

  // Unsubscribe from email updates
  const unsubscribeEmails = useCallback(() => {
    if (globalSocket && globalSocket.connected) {
      globalSocket.emit('unsubscribe_emails');
      console.log('📧 Unsubscribed from email updates');
    }
  }, []);

  // Subscribe to WhatsApp updates
  const subscribeWhatsApp = useCallback(() => {
    if (globalSocket && globalSocket.connected) {
      globalSocket.emit('subscribe_whatsapp');
      console.log('💬 Subscribed to WhatsApp updates');
    }
  }, []);

  // Unsubscribe from WhatsApp updates
  const unsubscribeWhatsApp = useCallback(() => {
    if (globalSocket && globalSocket.connected) {
      globalSocket.emit('unsubscribe_whatsapp');
      console.log('💬 Unsubscribed from WhatsApp updates');
    }
  }, []);

  // Subscribe to social media updates
  const subscribeSocialMedia = useCallback(() => {
    if (globalSocket && globalSocket.connected) {
      globalSocket.emit('subscribe_social_media');
      console.log('🌐 Subscribed to social media updates');
    }
  }, []);

  // Unsubscribe from social media updates
  const unsubscribeSocialMedia = useCallback(() => {
    if (globalSocket && globalSocket.connected) {
      globalSocket.emit('unsubscribe_social_media');
      console.log('🌐 Unsubscribed from social media updates');
    }
  }, []);

  // Ping server
  const ping = useCallback(() => {
    if (globalSocket && globalSocket.connected) {
      globalSocket.emit('ping');
    }
  }, []);

  return {
    connected,
    socketId,
    lastEvent,
    subscribeEmails,
    unsubscribeEmails,
    subscribeWhatsApp,
    unsubscribeWhatsApp,
    subscribeSocialMedia,
    unsubscribeSocialMedia,
    ping
  };
};

// Export global socket getter for advanced use cases
export const getGlobalSocket = () => globalSocket;

// Cleanup function (can be called on app unmount if needed)
export const disconnectWebSocket = () => {
  if (globalSocket) {
    globalSocket.disconnect();
    globalSocket = null;
  }
};
