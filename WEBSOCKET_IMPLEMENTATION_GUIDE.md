# Real-Time WebSocket Implementation - Complete Guide

## 🎯 Overview
Your email and WhatsApp system now has **real-time WebSocket listening** enabled. Instead of polling for new messages at fixed intervals, the system now **pushes instant notifications** to all connected clients when emails or messages arrive.

## ✅ What's Implemented

### 1. Backend WebSocket Server (Flask-SocketIO)
- **File**: `backend/app/socket_events.py`
- **Features**:
  - Real-time connection management
  - Client subscription/unsubscription channels
  - Broadcast functions for events
  - Health checks (ping/pong)

### 2. Email Real-Time Updates
- **Integration Point**: `backend/app/api/email_scheduling.py`
- **How It Works**:
  - When `handle_email_check()` runs (every EMAIL_CHECK_INTERVAL minutes), it:
    1. Fetches unread emails from IMAP
    2. Broadcasts `new_email` event for each email
    3. Broadcasts `emails_checked` summary
    4. All connected WebSocket clients receive instant notifications

### 3. WhatsApp Real-Time Updates  
- **Integration Point**: `backend/app/api/social_media.py`
- **How It Works**:
  - When webhook receives incoming WhatsApp message:
    1. Stores message in database
    2. Broadcasts `new_message` event immediately
    3. If auto-response enabled, broadcasts `response_sent` after AI generates response
    4. All subscribed clients get instant toast notifications

### 4. Frontend React Hook
- **File**: `frontend/src/hooks/useWebSocket.js`
- **Features**:
  - Singleton socket connection (reused across components)
  - Auto-reconnection with exponential backoff
  - Toast notifications for incoming events
  - Subscribe/unsubscribe functions

### 5. Integration with Email UI
- **File**: `frontend/src/pages/EmailTab.jsx`
- **Features**:
  - Subscribes to email updates on mount
  - Auto-refreshes email list when new emails arrive
  - Toast notifications show immediately

## 🚀 Installation & Setup

### Step 1: Install Backend Dependencies
```bash
cd backend
pip install flask-socketio>=5.3 python-socketio>=5.9 python-engineio>=4.7
# Or reinstall all dependencies:
pip install -r requirements.txt
```

### Step 2: Install Frontend Dependencies
```bash
cd frontend
npm install socket.io-client
# Or reinstall all:
npm install
```

### Step 3: Start the Backend
```bash
cd backend
python run.py
# You should see:
# ✓ WebSocket (SocketIO) initialized for real-time updates
# ✓ WebSocket (SocketIO) enabled - Real-time email and WhatsApp listening active
```

### Step 4: Start the Frontend
```bash
cd frontend
npm run dev
```

### Step 5: Verify Connection
**Browser Console** (Frontend):
```
✓ WebSocket connected: <socket_id>
✓ Connected to Brainr real-time service
📧 Subscribed to email updates
```

**Server Logs** (Backend):
```
✓ Client connected: <socket_id> (Total: 1)
✓ Client subscribed to emails: <socket_id>
```

## 📊 Event Types & Payloads

### Email Events

#### `new_email` Event
Emitted when a new email is fetched:
```json
{
  "event_type": "new_email",
  "email": {
    "id": "email_123",
    "from": "sender@example.com",
    "subject": "Important Meeting",
    "date": "2024-01-15T10:30:00Z",
    "preview": "Here's the agenda for tomorrow's..."
  },
  "timestamp": "2024-01-15T10:30:15Z",
  "recipients": 2
}
```

#### `emails_checked` Event
Emitted as summary after check:
```json
{
  "event_type": "emails_checked",
  "email": {
    "total_checked": 5,
    "new_emails": 5,
    "timestamp": "2024-01-15T10:30:15Z"
  },
  "timestamp": "2024-01-15T10:30:15Z"
}
```

### WhatsApp Events

#### `new_message` Event
Emitted when WhatsApp message received:
```json
{
  "event_type": "new_message",
  "message": {
    "message_id": "msg_456",
    "sender_id": "+234812345678",
    "sender_name": "John Doe",
    "message": "What's the status on the project?",
    "account": "My WhatsApp",
    "is_owner": true,
    "timestamp": "2024-01-15T10:35:00Z"
  },
  "timestamp": "2024-01-15T10:35:02Z",
  "recipients": 2
}
```

#### `response_sent` Event
Emitted when AI auto-response is sent:
```json
{
  "event_type": "response_sent",
  "message": {
    "message_id": "msg_456",
    "sender_id": "+234812345678",
    "response": "The project is on track. Deliverables expected by Friday.",
    "account": "My WhatsApp",
    "timestamp": "2024-01-15T10:35:05Z"
  },
  "timestamp": "2024-01-15T10:35:05Z"
}
```

## 🎮 Frontend Usage

### Using useWebSocket Hook
```jsx
import { useWebSocket } from '../hooks/useWebSocket'

function MyComponent() {
  const { 
    connected,           // boolean - connection status
    socketId,           // string - unique client ID
    subscribeEmails,    // function - subscribe to email events
    subscribeWhatsApp,  // function - subscribe to WhatsApp events
    lastEvent           // object - last received event
  } = useWebSocket()

  // Auto-subscribe on mount
  useEffect(() => {
    if (connected) {
      subscribeEmails()
    }
  }, [connected])

  // Handle incoming events
  useEffect(() => {
    if (lastEvent?.type === 'email') {
      console.log('New email:', lastEvent.data.email)
      // Refresh UI, trigger API calls, etc.
    }
  }, [lastEvent])

  return (
    <div>
      Status: {connected ? '🟢 Connected' : '🔴 Disconnected'}
      Socket ID: {socketId}
    </div>
  )
}
```

### Auto-Refresh on Email Arrival
Already implemented in `EmailTab.jsx`:
```jsx
useEffect(() => {
  if (lastEvent?.type === 'email' && lastEvent.data.event_type === 'new_email') {
    loadEmails('socket-update')  // Refresh email list
  }
}, [lastEvent])
```

## ⚙️ Configuration

### Email Check Interval
Set in `.env`:
```bash
EMAIL_CHECK_INTERVAL=5  # Check for new emails every 5 minutes
```

**Note**: With WebSocket, you no longer need frequent polling. Real-time events are pushed instantly. Keep EMAIL_CHECK_INTERVAL for periodic checks, but also get instant notifications when available.

### WebSocket Server Configuration
In `backend/app/socket_events.py`:
```python
socketio = SocketIO(
    app,
    cors_allowed_origins="*",      # Adjust for production
    async_mode='threading',         # Use 'eventlet' or 'gevent' for production
    transports=['websocket', 'polling']  # Fallback to polling if WebSocket fails
)
```

## 🔍 Monitoring & Debugging

### Check Connected Clients
**Backend Endpoint** (add if needed):
```bash
GET /api/websocket/status
```

### View Event Logs
Enable debug logging in `.env`:
```bash
FLASK_ENV=development  # Shows WebSocket connection logs
```

### Frontend Console
Check browser DevTools → Console:
```
✓ WebSocket connected
✓ Subscribed to emails
📧 Email update received
```

## 🚨 Troubleshooting

### "WebSocket not connecting"
1. Check backend is running: `python run.py`
2. Verify WebSocket server started: Look for "✓ WebSocket initialized" log
3. Check CORS settings if frontend is on different origin
4. Try HTTP polling fallback: Check transports config

### "No real-time updates received"
1. Verify client subscribed: Check browser console
2. Check EMAIL_CHECK_INTERVAL setting in `.env`
3. Trigger manual email check: Use "Load Emails" button in UI
4. Check backend logs for broadcast errors

### "Connection drops frequently"
1. Check network stability
2. Adjust reconnection settings in `useWebSocket.js`
3. Use `async_mode='eventlet'` in production (install: `pip install eventlet`)

## 📈 Performance Considerations

### Broadcast Efficiency
- Events only sent to **subscribed** clients
- Logged when no subscribed clients available
- Minimal message payload (headers + essential data only)

### Database Impact
- Messages still stored in database (for history)
- WebSocket is **in addition to** database storage, not replacement
- No excessive queries - just INSERT on message arrival

### Connection Management
- Auto-reconnection with exponential backoff (1s → 5s)
- Idle connections maintained with ping/pong health checks
- Graceful cleanup on disconnect

## 🔒 Security Notes

### For Production:
1. **Change CORS**: Restrict `cors_allowed_origins` to your domain
```python
cors_allowed_origins=["https://yourdomain.com"]
```

2. **Add Authentication**: Implement JWT token validation on connect
```python
@socketio.on('connect')
def handle_connect(auth):
    token = auth.get('token')
    if not validate_token(token):
        raise ConnectionRefusedError('Invalid token')
```

3. **Use HTTPS/WSS**: In production, use secure WebSocket (wss://)

4. **Rate Limiting**: Add per-client event rate limits

## 📝 API Reference

### Socket Events Emitted (Server → Client)

| Event | Emitted When | Data |
|-------|-------------|------|
| `connected` | Client connects | Client ID, service info |
| `email_update` | Email event | Email data, event type |
| `whatsapp_update` | WhatsApp event | Message data, event type |
| `social_media_update` | Social media event | Channel, message, event type |
| `subscribed` | Client subscribes | Channel name |
| `unsubscribed` | Client unsubscribes | Channel name |
| `pong` | Server responds to ping | Timestamp, client count |

### Socket Events Expected (Client → Server)

| Event | Purpose | Data |
|-------|---------|------|
| `subscribe_emails` | Subscribe to emails | (none) |
| `subscribe_whatsapp` | Subscribe to WhatsApp | (none) |
| `subscribe_social_media` | Subscribe to all social | (none) |
| `unsubscribe_*` | Unsubscribe from channel | (none) |
| `ping` | Health check | (none) |

## 🎯 Next Steps

### Recommended Enhancements
1. **Add WebSocket Status Display**: Show connection indicator in UI
2. **Message Notifications**: Toast alerts in top-right (✅ already done)
3. **Offline Queue**: Buffer messages if WebSocket offline
4. **Admin Dashboard**: Show connected clients, events rate
5. **Advanced Filtering**: Subscribe to specific email senders
6. **Message Acknowledgment**: Confirm receipt with ACK messages

### Integration with Existing Features
- ✅ Email auto-checking still works
- ✅ WhatsApp webhook still works  
- ✅ Database storage still works
- ✅ All existing endpoints still work
- ✅ Nothing was removed, only enhanced with real-time

## 📚 Files Modified Summary

```
Backend:
  - app/__init__.py (SocketIO initialization)
  - app/socket_events.py (NEW - WebSocket server)
  - app/api/email_scheduling.py (broadcast on email check)
  - app/api/social_media.py (broadcast on message)
  - run.py (use socketio.run())
  - requirements.txt (add flask-socketio, python-socketio)

Frontend:
  - src/hooks/useWebSocket.js (NEW - WebSocket client)
  - src/pages/EmailTab.jsx (integrate hook)
  - package.json (add socket.io-client)
```

## ✅ Validation Checklist

- [ ] Backend starts with "✓ WebSocket initialized" message
- [ ] Frontend connects and shows socket ID in console
- [ ] Email refresh button still works (manual)
- [ ] Automatic email check still runs every N minutes
- [ ] New emails appear in real-time when check runs
- [ ] Toast notifications appear for new emails
- [ ] WhatsApp webhook still receives messages
- [ ] WhatsApp messages appear in real-time
- [ ] Toast notifications appear for WhatsApp messages
- [ ] Reconnects automatically when connection drops
- [ ] No errors in browser console or backend logs

---

**Questions?** Check the architecture diagrams in the conversation summary or the logs for detailed event information.
