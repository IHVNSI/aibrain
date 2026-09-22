# WebSocket Real-Time Implementation - Verification Checklist

## ✅ Pre-Installation Checklist

- [ ] Python 3.8+ installed (`python --version`)
- [ ] pip working (`pip --version`)
- [ ] Node.js 14+ installed (`node --version`) - Optional but recommended
- [ ] npm working (`npm --version`) - Optional but recommended
- [ ] Terminal/PowerShell open in project root

---

## 🔧 Installation Steps

### Step 1: Install Backend Dependencies

**Windows (PowerShell):**
```powershell
cd backend
pip install flask-socketio>=5.3 python-socketio>=5.9 python-engineio>=4.7
```

**macOS/Linux:**
```bash
cd backend
pip install flask-socketio>=5.3 python-socketio>=5.9 python-engineio>=4.7
```

Or run the setup script:
- Windows: `setup-websocket.bat`
- macOS/Linux: `bash setup-websocket.sh`

**Verification:**
```bash
python -c "import flask_socketio; print('✓ flask-socketio'); import socketio; print('✓ socketio')"
```

Expected output:
```
✓ flask-socketio
✓ socketio
```

### Step 2: Install Frontend Dependencies

**In `frontend/` directory:**
```bash
npm install socket.io-client
# or install all:
npm install
```

**Verification:**
```bash
npm list socket.io-client
```

Expected output:
```
frontend@0.1.0 /path/to/frontend
└── socket.io-client@4.7.2
```

---

## 🚀 Running the Application

### Terminal 1: Start Backend
```bash
cd backend
python run.py
```

**Expected output:**
```
Changed working directory to: /path/to/brainr
Starting Brainr server from: /path/to/brainr
Project root: /path/to/brainr
Backend root: /path/to/brainr/backend
Port: 5001
Debug: True
✓ WebSocket (SocketIO) initialized for real-time updates
✓ WebSocket (SocketIO) enabled - Real-time email and WhatsApp listening active
 * Running on http://0.0.0.0:5001
 * Restarting with reloader
 * Debugger is active!
```

**Green lights to look for:**
- ✓ WebSocket (SocketIO) initialized
- ✓ WebSocket (SocketIO) enabled
- Running on http://0.0.0.0:5001

### Terminal 2: Start Frontend
```bash
cd frontend
npm run dev
```

**Expected output:**
```
VITE v5.4.8  ready in 234 ms

➜  Local:   http://localhost:5173/
➜  press h to show help
```

**Green lights to look for:**
- Local URL available
- No errors in output

---

## 🔍 Verification Steps

### Check 1: WebSocket Connection

**In Browser Console** (DevTools → Console):

1. Open your app at `http://localhost:5173/`
2. Open browser DevTools: `F12` or `Right-click → Inspect`
3. Click on "Console" tab
4. Look for messages like:

```
✓ WebSocket connected: socket_abc123xyz
✓ Connected to Brainr real-time service
📧 Subscribed to email updates
```

**Status:** 
- ✅ If you see these messages, WebSocket is working
- ❌ If you see connection errors, check backend is running

### Check 2: Backend Connection Status

**In Backend Console:**

Look for messages like:
```
✓ Client connected: socket_abc123xyz (Total: 1)
✓ Client subscribed to emails: socket_abc123xyz
```

**Status:**
- ✅ If you see these, frontend connected successfully
- ❌ If missing, check CORS settings

### Check 3: Email Real-Time Updates

1. Click "Settings" → "Email Configuration"
2. Verify email is configured (test connection works)
3. In Console, wait for scheduled email check (every EMAIL_CHECK_INTERVAL minutes)
4. Or manually click "Load Emails" button in Email tab
5. Look for console messages:
   ```
   📧 Email update received: {...}
   ```
6. Should see emails appear in list in real-time

**Status:**
- ✅ New emails appear without manual refresh
- ✅ Toast notification appears "New Email from sender@example.com"
- ❌ Nothing happens → Check EMAIL_CHECK_INTERVAL setting

### Check 4: WhatsApp Real-Time Updates

1. Set up WhatsApp account in Settings → Social Media
2. Send a WhatsApp message to configured number
3. Look for console messages:
   ```
   💬 WhatsApp update received: {...}
   ```
4. Should see message appear in WhatsApp section
5. Should see toast notification

**Status:**
- ✅ Message appears instantly
- ✅ Toast notification appears
- ❌ Nothing happens → Check webhook is properly configured

---

## 📊 Live Monitoring Dashboard

### Backend Logs to Monitor

**Email Check Cycle:**
```
✓ Email check completed: 3 unread emails
📧 Broadcasting email event to 1 clients
```

**WhatsApp Message:**
```
Received whatsapp message from +234812345678: What's the status?
✓ Client subscribed to whatsapp: socket_xyz
Broadcasting whatsapp event to 1 clients
```

### Browser Console Events

**Email Events:**
```
email_update received:
  - event_type: "new_email"
  - email: { from, subject, date }
  - recipients: 1
```

**WhatsApp Events:**
```
whatsapp_update received:
  - event_type: "new_message"
  - message: { sender_id, sender_name, message_text }
  - recipients: 1
```

---

## 🚨 Troubleshooting

### Issue: "WebSocket connection failed"

**Possible Causes:**
1. Backend not running
2. Wrong backend URL in frontend config
3. CORS not configured
4. Firewall blocking port 5001

**Solutions:**
```bash
# Verify backend is running
curl http://localhost:5001/api/health

# Check backend logs for errors
# Look for: "Running on http://0.0.0.0:5001"

# If using different hostname, check frontend config
# REACT_APP_API_URL in .env or frontend/src/hooks/useWebSocket.js
```

### Issue: "Connected but no email/WhatsApp events"

**Possible Causes:**
1. EMAIL_CHECK_INTERVAL not set
2. Email service not configured
3. WhatsApp webhook not enabled
4. Client not subscribed to channel

**Solutions:**
```bash
# Check EMAIL_CHECK_INTERVAL in .env
grep EMAIL_CHECK_INTERVAL .env

# Manually trigger email check
curl -X POST http://localhost:5001/api/email/check

# Check subscription in console
# Should see: "📧 Subscribed to email updates"
```

### Issue: "Connection drops frequently"

**Possible Causes:**
1. Unstable network
2. Server resource constraints
3. Too many open connections
4. Firewall timeout settings

**Solutions:**
```bash
# Check backend resource usage
# Look for memory/CPU spikes in logs

# Restart backend (it will auto-reconnect)
python run.py

# Adjust in useWebSocket.js:
reconnectionDelay: 1000,      # Wait 1s before reconnect
reconnectionDelayMax: 5000,   # Max 5s between attempts
```

### Issue: "Firewall/Proxy blocking WebSocket"

**Possible Causes:**
1. Corporate firewall blocking port 5001
2. Reverse proxy not configured for WebSocket
3. Network policy restricting WebSocket

**Solutions:**
```bash
# Try HTTP polling fallback
# In useWebSocket.js:
transports: ['polling', 'websocket']  # Try polling first

# Check network in DevTools
# Network tab → WS should show connection
```

---

## 📈 Performance Monitoring

### Check CPU Usage
**Backend Console:**
```
# Should see low CPU with no heavy loops
# email_check should complete in <5 seconds
✓ Email check completed: 5 unread emails (completed in 2.3s)
```

### Check Memory Usage
**Backend Console:**
```
# Should not see memory growing unbounded
# Each WebSocket connection uses ~1-2MB
Connected clients: 1, Memory: ~50MB
```

### Check Network Traffic
**Browser DevTools → Network:**
```
- WS connection should stay open
- Messages should be <1KB each
- 1 message per email received
```

---

## ✅ Final Verification

Run this checklist to confirm everything is working:

- [ ] Backend starts with "✓ WebSocket initialized"
- [ ] Frontend connects and shows socket ID in console
- [ ] "Subscribed to email updates" message appears
- [ ] Email refresh button still works (manual)
- [ ] Automatic email check still runs
- [ ] New emails appear in real-time
- [ ] Toast notifications appear for emails
- [ ] WhatsApp webhook receives messages
- [ ] WhatsApp messages appear in real-time
- [ ] Toast notifications appear for WhatsApp
- [ ] Reconnects automatically after disconnect
- [ ] No errors in browser console
- [ ] No errors in backend logs
- [ ] Database still stores emails/messages
- [ ] All existing features still work

---

## 🎉 Success Indicators

### You'll know it's working when:

1. **Email arrives instantly**
   - New email appears in list immediately
   - Toast notification pops up
   - No refresh button needed

2. **WhatsApp works in real-time**
   - Message appears immediately
   - Toast notification shows sender name
   - Response sent instantly

3. **Automatic checks continue**
   - EMAIL_CHECK_INTERVAL still runs
   - Scheduler logs show regular checks
   - WebSocket broadcasts for each check

4. **Seamless experience**
   - No manual refresh needed
   - Multiple users see updates
   - Connection recovers automatically

---

## 📞 Getting Help

If something doesn't work:

1. **Check the logs:**
   ```bash
   # Backend logs show connection/event details
   # Frontend console shows WebSocket activity
   ```

2. **Read the guide:**
   ```bash
   cat WEBSOCKET_IMPLEMENTATION_GUIDE.md
   ```

3. **Check configuration:**
   ```bash
   # Verify .env settings
   grep "EMAIL_CHECK_INTERVAL\|EMAIL_ADDRESS" .env
   ```

4. **Test manually:**
   ```bash
   # Test email connection
   python -c "from app.email_service import EmailConfig; print(EmailConfig.get_email_service())"
   
   # Test WebSocket connection
   curl -i http://localhost:5001/api/health
   ```

---

**Congratulations!** 🎉 Your real-time WebSocket system is now operational.

For more details, see: [WEBSOCKET_IMPLEMENTATION_GUIDE.md](WEBSOCKET_IMPLEMENTATION_GUIDE.md)
