# WhatsApp Web Login - Setup Guide

## 🎯 Overview

You can now **login to your personal WhatsApp** directly without needing WhatsApp API access. This uses WhatsApp Web automation with Selenium to send and receive messages through your browser.

---

## ✨ Features

✅ **Login via QR Code** - Scan with your phone, just like WhatsApp Web  
✅ **Send Messages** - Send to any contact via phone number  
✅ **View Chats** - See your recent chats  
✅ **Read Messages** - View chat history  
✅ **No API Required** - Uses your personal WhatsApp account  
✅ **Auto-Session** - Stays logged in between sessions  

---

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
cd backend
pip install selenium webdriver-manager pyqrcode

# Or reinstall all:
pip install -r requirements.txt
```

**Verify:**
```bash
python -c "import selenium; print('✓ Selenium installed')"
python -c "import webdriver_manager; print('✓ Webdriver Manager installed')"
```

### Step 2: Start Backend & Frontend

```bash
# Terminal 1 - Backend
cd backend
python run.py

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### Step 3: Login to WhatsApp

1. Go to Settings → WhatsApp (Web)
2. Click "Login with WhatsApp"
3. **Chrome window opens automatically**
4. **Scan the QR code** with your WhatsApp phone
5. **✓ Done!** You're now connected

---

## 📱 How to Use

### Send a Message

1. In the "Send Message" section:
   - Enter phone number: `+1234567890` (with country code)
   - Type your message
   - Click "Send Message"
2. Message is sent instantly
3. Success notification appears

**Example:**
```
Phone: +234812345678
Message: Hello! How are you?
```

### View Chat History

1. In the "Recent Chats" sidebar:
   - Your chats appear automatically
   - Click on any chat name
   - Messages load below

2. Refresh button updates chat list

---

## 🔑 Important Notes

### Session Management
- Your login session is **stored locally** in `whatsapp_sessions/` folder
- You stay logged in between restarts
- No need to scan QR code every time
- **First login only** requires QR code scan

### Phone Requirements
- WhatsApp must be installed on your phone
- Keep your phone nearby when scanning QR code
- Phone stays connected to WhatsApp Web (standard WhatsApp behavior)

### Browser
- **Chrome/Chromium required** (automatically managed)
- Browser window opens automatically during login
- No manual browser control needed
- Window closes after login

---

## 📝 API Reference

### Endpoints

#### 1. Login to WhatsApp
```
POST /api/whatsapp/login
```

**Request:**
```json
{
  "session_name": "default"  (optional)
}
```

**Response:**
```json
{
  "success": true,
  "message": "Logged in to WhatsApp Web",
  "session_name": "default"
}
```

#### 2. Check Login Status
```
GET /api/whatsapp/status?session_name=default
```

**Response:**
```json
{
  "logged_in": true,
  "session_name": "default",
  "timestamp": "2024-09-22T10:30:00Z"
}
```

#### 3. Send Message
```
POST /api/whatsapp/send
```

**Request:**
```json
{
  "phone_number": "+1234567890",
  "message": "Hello!",
  "session_name": "default"  (optional)
}
```

**Response:**
```json
{
  "success": true,
  "message": "Message sent",
  "phone_number": "+1234567890"
}
```

#### 4. Get Chats
```
GET /api/whatsapp/chats?session_name=default&limit=15
```

**Response:**
```json
{
  "success": true,
  "chats": [
    {"name": "Mom"},
    {"name": "Work Group"},
    {"name": "Best Friend"}
  ]
}
```

#### 5. Get Messages
```
POST /api/whatsapp/messages
```

**Request:**
```json
{
  "chat_name": "Mom",
  "limit": 30,
  "session_name": "default"  (optional)
}
```

**Response:**
```json
{
  "success": true,
  "chat_name": "Mom",
  "messages": [
    {
      "text": "Hi, how are you?",
      "time": "1234567890",
      "incoming": true
    },
    {
      "text": "I'm fine!",
      "time": "1234567891",
      "incoming": false
    }
  ]
}
```

#### 6. Logout
```
POST /api/whatsapp/logout
```

**Request:**
```json
{
  "session_name": "default"  (optional)
}
```

**Response:**
```json
{
  "success": true,
  "message": "Logged out from WhatsApp Web"
}
```

---

## 🐛 Troubleshooting

### "Connection refused" or Backend Error

**Problem:** Backend won't start or WhatsApp service crashes

**Solutions:**
1. Check Python packages installed:
   ```bash
   pip list | grep -E "selenium|webdriver"
   ```

2. Reinstall dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. Clear old Chrome profiles (if login issues):
   ```bash
   rm -rf whatsapp_sessions/  # Clear saved sessions
   ```

4. Check Chrome/Chromium installed:
   ```bash
   which google-chrome  # On Linux
   # or should auto-download
   ```

### "QR Code Not Appearing"

**Problem:** Browser opens but no QR code shows

**Solutions:**
1. Wait 10-15 seconds for page to load
2. Close and retry login
3. Check internet connection
4. Clear browser cache in Chrome settings

### "Message Not Sending"

**Problem:** Message sends but fails

**Solutions:**
1. Verify phone number format: `+<country><number>`
   - ✓ Correct: `+1234567890`
   - ✗ Wrong: `1234567890` or `00234567890`

2. Check if you're still logged in:
   - Click "Status" to verify connection
   - Login again if needed

3. Check message text not empty

4. Try sending to yourself first to test

### "Chats Not Loading"

**Problem:** Recent chats list is empty

**Solutions:**
1. Click "Refresh Chats" button
2. Make sure you're logged in
3. Start a conversation on WhatsApp phone
4. Wait a few seconds and refresh again

### "Session Not Persisting"

**Problem:** Need to scan QR code every time

**Solutions:**
1. Session folder must exist: `whatsapp_sessions/`
2. Check folder permissions (must be writable)
3. Don't delete `whatsapp_sessions/` folder between sessions
4. Check disk space available

---

## 🔒 Security & Privacy

### What's Stored?
- **Local Session Files**: Chrome user profile with login info
- **Location**: `backend/whatsapp_sessions/`
- **Encrypted**: By Chrome (standard browser behavior)

### What's NOT Stored?
- ❌ No messages backed up
- ❌ No contacts exported
- ❌ No encryption keys shared
- ❌ No external API calls

### Safety
- ✓ Only you control your account
- ✓ Browser automation is local (not cloud)
- ✓ Same as WhatsApp Web in desktop browser
- ✓ No third-party service involved

---

## 📈 Advanced Usage

### Multiple Accounts

You can manage multiple WhatsApp accounts:

```python
# Each account has its own session
wa1 = WhatsAppManager.get_instance("account1")
wa2 = WhatsAppManager.get_instance("account2")

# They store separately in:
# - whatsapp_sessions/account1_data/
# - whatsapp_sessions/account2_data/
```

**Via API:**
```bash
# Login to account 1
curl -X POST http://localhost:5001/api/whatsapp/login \
  -H "Content-Type: application/json" \
  -d '{"session_name": "account1"}'

# Send from account 2
curl -X POST http://localhost:5001/api/whatsapp/send \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1234567890",
    "message": "Hi!",
    "session_name": "account2"
  }'
```

### Automation Examples

**Send Scheduled Messages:**
```python
from app.whatsapp_service import WhatsAppManager
from datetime import datetime, timedelta
import time

wa = WhatsAppManager.get_instance()

# Schedule a message
message = "Meeting at 3 PM today"
recipient = "+1234567890"

# Send after 2 hours
time.sleep(2 * 60 * 60)
wa.send_message(recipient, message)
```

**Backup Chat History:**
```python
messages = wa.get_messages("Friend Name", limit=100)
with open("chat_backup.txt", "w") as f:
    for msg in messages:
        direction = "→" if msg['incoming'] else "←"
        f.write(f"{direction} {msg['text']}\n")
```

---

## ✅ Validation Checklist

After setup, verify:

- [ ] Backend starts without errors
- [ ] Frontend loads Settings → WhatsApp (Web) tab
- [ ] "Login with WhatsApp" button appears
- [ ] Clicking login opens Chrome window
- [ ] QR code appears in Chrome window
- [ ] Phone scan is successful
- [ ] "✓ Logged In" message appears
- [ ] Status shows "🟢 Connected"
- [ ] Can enter phone number and message
- [ ] Message sends successfully
- [ ] Chats list shows up
- [ ] Can click on chat to view messages
- [ ] Logout button works
- [ ] Session persists after restart

---

## 📞 Getting Help

### Check Logs
```bash
# Backend logs show connection details
python run.py 2>&1 | grep -i "whatsapp\|qr\|login"

# Frontend browser console (F12)
# Look for error messages
```

### Test Manually
```bash
# Check if backend is running
curl http://localhost:5001/api/whatsapp/status

# Test send message
curl -X POST http://localhost:5001/api/whatsapp/send \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890", "message": "test"}'
```

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| "No Chrome found" | Chrome/Chromium not installed | Webdriver manager will auto-install |
| "QR code timeout" | Network/browser issue | Check internet, retry login |
| "Message not sending" | Wrong phone format | Use +<country><number> |
| "Session not loading" | File permissions | Check whatsapp_sessions/ folder |
| "Browser won't close" | Selenium issue | Manual close or restart |

---

## 🎉 Success!

You now have **full WhatsApp integration without any API**. 

### What You Can Do
✅ Send messages programmatically  
✅ Receive messages automatically  
✅ Manage multiple accounts  
✅ Build WhatsApp automations  
✅ Integrate with Brainr workflows  

### Next Steps
1. ✓ Setup complete - you're ready to use!
2. Try sending a test message
3. Build automations on top
4. Share with your team

---

**Questions?** Check the troubleshooting section above or read the code comments in `backend/app/whatsapp_service.py`.

*WhatsApp Web Login Integration - Ready for Production*
