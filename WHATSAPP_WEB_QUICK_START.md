# WhatsApp Web Login - Quick Start

## ⚡ 2-Minute Setup

### 1️⃣ Install
```bash
cd backend
pip install selenium webdriver-manager pyqrcode
```

### 2️⃣ Start Services
```bash
# Terminal 1
cd backend && python run.py

# Terminal 2  
cd frontend && npm run dev
```

### 3️⃣ Login
1. Open http://localhost:5173
2. Go to **Settings → WhatsApp (Web)**
3. Click **"Login with WhatsApp"**
4. **Scan QR code** with your phone
5. Done! 🎉

---

## 📱 Send Your First Message

1. In "Send Message" section:
   - Phone: `+1234567890` (include country code!)
   - Message: `Hello from Brainr!`
   - Click Send

2. Check your phone - message arrived! ✓

---

## 🆘 Troubleshooting

### "Backend won't start"
```bash
pip install -r backend/requirements.txt
python run.py
```

### "Chrome not opening"
- Webdriver Manager auto-installs Chrome
- May take 30s first time
- Be patient!

### "QR code not showing"
- Wait 10-15 seconds
- Check internet connection
- Try logout and login again

### "Message not sending"
- Phone number format: **+<country><digits>**
- ✓ `+1234567890`
- ✗ `1234567890`
- ✗ `00234567890`

---

## 📖 Full Docs

Read **WHATSAPP_WEB_LOGIN_GUIDE.md** for:
- Detailed API reference
- Advanced usage
- Security notes
- Multiple accounts
- Automation examples

---

**That's it!** You're ready to send WhatsApp messages from Brainr. 🚀
