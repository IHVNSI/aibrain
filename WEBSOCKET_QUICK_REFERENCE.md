# WebSocket Quick Reference Card

## 🚀 Quick Start
```bash
# Install
setup-websocket.bat          # Windows
bash setup-websocket.sh      # macOS/Linux

# Run
cd backend && python run.py  # Terminal 1
cd frontend && npm run dev   # Terminal 2
```

## ✅ Status Checks

### Backend Started Successfully?
Look for in terminal:
```
✓ WebSocket (SocketIO) initialized
✓ WebSocket (SocketIO) enabled
Running on http://0.0.0.0:5001
```

### Frontend Connected?
Look for in browser console (F12):
```
✓ WebSocket connected: <socket_id>
✓ Connected to Brainr real-time service
📧 Subscribed to email updates
```

### Email Working?
```
✓ Email check completed: X unread emails
Broadcasting email event to Y clients
```

### WhatsApp Working?
```
Received whatsapp message from +XXX
Broadcasting whatsapp event to Y clients
```

---

## 🔍 Quick Debugging

### WebSocket Not Connecting?
```bash
# Check if backend is running
curl http://localhost:5001/api/health

# Check backend logs for:
# - "Running on http://0.0.0.0:5001"
# - No error messages
```

### No Real-Time Updates?
```bash
# 1. Verify subscription in browser console:
# Should see: "📧 Subscribed to email updates"

# 2. Check EMAIL_CHECK_INTERVAL:
grep EMAIL_CHECK_INTERVAL .env

# 3. Trigger manual check:
# Click "Load Emails" button in UI
# Or wait for next scheduled check
```

### Emails Not Showing?
```bash
# 1. Verify email config works
# Click "Test Connection" in Settings

# 2. Check email folder
# Make sure looking at INBOX, not Sent/Drafts

# 3. Check unread emails exist
# IMAP should show at least 1 unread email
```

### Connection Drops?
```bash
# Should auto-reconnect in 1-5 seconds
# Check browser console for:
# "WebSocket disconnected: <reason>"
# Then: "WebSocket reconnected"

# If not auto-reconnecting:
# Hard refresh: Ctrl+F5 or Cmd+Shift+R
# Restart both backend and frontend
```

---

## 🎯 Event Checklist

### Email Events
- [ ] **new_email** - New email received
- [ ] **emails_checked** - Check completed (summary)
- [ ] **toast alert** - "New Email from..."

### WhatsApp Events  
- [ ] **new_message** - Message received
- [ ] **response_sent** - AI response sent
- [ ] **toast alert** - "WhatsApp Message from..."

---

## 📊 Performance Metrics

| Metric | Expected | Bad |
|--------|----------|-----|
| Connection time | <1s | >5s |
| Email event latency | <100ms | >1s |
| Memory per connection | 1-2MB | >5MB |
| CPU usage idle | <1% | >20% |

---

## 🔐 Configuration Checklist

### Backend
```bash
# .env
EMAIL_CHECK_INTERVAL=5        # ✓ Email check every 5 min
EMAIL_ADDRESS=<email>         # ✓ Valid email configured
EMAIL_PASSWORD=<password>     # ✓ App password (not account password)
```

### Frontend
```bash
# .env or useWebSocket.js
REACT_APP_API_URL=http://localhost:5001  # ✓ Correct backend URL
```

### Node Modules
```bash
# frontend/node_modules
socket.io-client@^4.7.2       # ✓ Installed via npm
```

### Python Packages
```bash
# backend/
flask-socketio>=5.3           # ✓ Installed via pip
python-socketio>=5.9          # ✓ Installed via pip
python-engineio>=4.7          # ✓ Installed via pip
```

---

## 🚨 SOS (Stop-On-Sight)

### Complete Failure Recovery
```bash
# 1. Stop everything
Ctrl+C in both terminals

# 2. Clear cache
# Browser: Ctrl+Shift+Delete → Clear all
# Frontend: rm -rf frontend/node_modules

# 3. Reinstall
bash setup-websocket.sh       # macOS/Linux
setup-websocket.bat           # Windows

# 4. Restart
cd backend && python run.py
cd frontend && npm run dev

# 5. Verify
# Browser console should show connection success
```

---

## 📝 File Locations

| What | Where |
|------|-------|
| Backend code | `backend/app/` |
| Socket events | `backend/app/socket_events.py` |
| Email scheduling | `backend/app/api/email_scheduling.py` |
| Frontend hook | `frontend/src/hooks/useWebSocket.js` |
| Email UI | `frontend/src/pages/EmailTab.jsx` |
| Config | `.env` |
| Requirements | `backend/requirements.txt` |
| Dependencies | `frontend/package.json` |

---

## 🔗 Related Documentation

- **Full Guide:** WEBSOCKET_IMPLEMENTATION_GUIDE.md
- **Verification:** WEBSOCKET_VERIFICATION_CHECKLIST.md
- **Summary:** WEBSOCKET_COMPLETE_SUMMARY.md

---

## 💡 Pro Tips

### Tip 1: Multiple Connections
```javascript
// Browser console
// Check how many clients connected to backend:
socket.emit('ping')  // Will get response with count
```

### Tip 2: Event Monitoring
```javascript
// Browser console - Listen to all events:
socket.onAny((eventName, ...args) => {
  console.log(`📡 Event: ${eventName}`, args)
})
```

### Tip 3: Manual Trigger
```bash
# Trigger email check from command line:
curl -X POST http://localhost:5001/api/email/check
```

### Tip 4: Network Debugging
```bash
# Browser DevTools → Network tab
# Filter: "ws"
# Should see: ws://localhost:5001/socket.io/?...
# Status: 101 Switching Protocols
```

### Tip 5: Backend Activity
```bash
# Watch backend logs in real-time:
python run.py 2>&1 | grep -i "socket\|broadcast\|email"
```

---

## 🎓 Troubleshooting Decision Tree

```
WebSocket Not Working?
│
├─ Browser shows "Connection refused"?
│  ├─ Backend running?
│  │  ├─ No → Start: cd backend && python run.py
│  │  └─ Yes → Check port 5001 is not blocked
│  └─ Check: curl http://localhost:5001/api/health
│
├─ Connected but no events?
│  ├─ Email configured?
│  │  ├─ No → Set up in Settings → Email Config
│  │  └─ Yes → Try "Test Connection" button
│  ├─ Check EMAIL_CHECK_INTERVAL
│  │  ├─ Not set? → Add to .env
│  │  └─ Set? → Wait or click "Load Emails"
│  └─ Check subscription: Console should show "📧 Subscribed"
│
├─ Connection drops frequently?
│  ├─ Network stable?
│  │  ├─ No → Fix network issues
│  │  └─ Yes → Continue
│  ├─ Server resources?
│  │  └─ Check memory/CPU usage
│  └─ Reconnecting? → Should happen auto in 1-5s
│
└─ Still not working?
   └─ Follow: WEBSOCKET_VERIFICATION_CHECKLIST.md
```

---

## ⚡ Emergency Contacts

### Backend Issues
```bash
# Check logs
python run.py  # Look for errors

# Most common:
# - ImportError → Missing dependency (pip install)
# - Address already in use → Port 5001 occupied
# - No module named 'flask_socketio' → pip install flask-socketio
```

### Frontend Issues
```bash
# Browser console (F12)
# Look for red errors

# Most common:
# - socket is not defined → npm install socket.io-client
# - Failed to fetch → Backend not running
# - CORs error → CORS not configured
```

### Installation Issues
```bash
# Windows only
# If setup-websocket.bat fails:
pip install --upgrade pip
pip install -r backend/requirements.txt

# macOS/Linux
# If bash setup-websocket.sh fails:
chmod +x setup-websocket.sh
bash setup-websocket.sh
```

---

## ✨ Success Signals

Look for these to confirm everything works:

### Backend
```
✓ WebSocket initialized
✓ Client connected
✓ Email check completed
Broadcasting event
```

### Frontend
```
✓ WebSocket connected
📧 Subscribed to email updates
email_update received
New toast notification
```

### Database
```
- Emails stored in database
- Sent emails tracked
- WhatsApp messages logged
- All existing queries work
```

---

## 📞 Quick Help Commands

```bash
# Test backend health
curl http://localhost:5001/api/health

# Test email configuration
python -c "from app.email_service import EmailConfig; \
           svc = EmailConfig.get_email_service(); \
           print('✓ Email service ready' if svc else '✗ Not configured')"

# List installed Python packages
pip list | grep -E "socketio|flask"

# List installed NPM packages
npm list socket.io-client

# Check port 5001 is open
netstat -an | grep 5001  # macOS/Linux
netstat -ano | findstr :5001  # Windows
```

---

**Print this card for quick reference while troubleshooting!**

*Last updated: 2024 | WebSocket Real-Time Implementation v1.0*
