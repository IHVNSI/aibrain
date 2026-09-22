# Gmail Email Configuration - Fix & Testing Guide

## Issues Fixed ✅

### 1. **Missing `imap_port` Parameter**
**Problem:** The email configuration endpoint was not passing the `imap_port` parameter when testing the connection, causing a TypeError.

**Fix:** Updated `backend/app/api/email_scheduling.py` to pass the `imap_port` parameter to `EmailService()`:
```python
# Before (incorrect)
service = EmailService(imap_server, email_address, email_password)

# After (correct)
service = EmailService(imap_server, email_address, email_password, imap_port)
```

### 2. **Missing Default IMAP/SMTP Servers for Gmail**
**Problem:** When user selects Gmail as provider but doesn't provide IMAP/SMTP servers, they were left empty, causing connection failures.

**Fix:** Added logic to auto-set default servers based on provider:
```python
provider_defaults = {
    'gmail': ('imap.gmail.com', 993, 'smtp.gmail.com', 587),
    'outlook': ('outlook.office365.com', 993, 'smtp.office365.com', 587),
    'yahoo': ('imap.mail.yahoo.com', 993, 'smtp.mail.yahoo.com', 465),
    'icloud': ('imap.mail.me.com', 993, 'smtp.mail.me.com', 587),
}
```

### 3. **Better Error Logging**
**Problem:** Connection errors weren't being logged with full traceback.

**Fix:** Added enhanced error logging with exc_info for debugging.

---

## Gmail Setup Guide

### Step 1: Generate Gmail App Password

Gmail doesn't allow regular passwords for third-party apps. You must use an **App Password**:

1. Go to: https://myaccount.google.com/apppasswords
2. Select **Mail** and **Windows Computer**
3. Google will generate a 16-character password
4. Copy this password (you'll need it in Step 2)

⚠️ **Important:** Use the app password, NOT your regular Gmail password!

### Step 2: Configure in Brainr

**Via Settings UI:**
1. Go to **Settings** → **Email** tab (admin only)
2. Click **Email Configuration** button
3. Fill in:
   - **Email Address:** your.email@gmail.com
   - **Email Password:** (paste the 16-char app password)
   - **Email Provider:** Gmail (dropdown)
   - **Test Connection:** ✓ (check this box)
4. Click **Save Configuration**
5. You should see: ✅ "✓ Connection successful"

**Expected Configuration:**
```json
{
  "email_address": "your.email@gmail.com",
  "email_password": "abcdefghijklmnop",
  "email_provider": "gmail",
  "imap_server": "imap.gmail.com",
  "imap_port": 993,
  "imap_tls": true,
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_tls": true,
  "test_connection": true
}
```

### Step 3: Verify Configuration

After saving, you should see:
- ✅ "Email configuration updated"
- ✅ "✓ Connection successful" (if test_connection was checked)

The configuration is saved to `.env` file and will persist even after restart.

---

## Testing Your Configuration

### Option 1: Using Settings UI (Recommended)

1. Go to Settings → Email
2. Click the green **"Load Emails"** button
3. You should see your email folders (INBOX, Drafts, Sent, etc.)
4. Click on a folder to view emails

### Option 2: Using Python Test Script

From the project root directory:

```bash
# Test script is provided
python test_gmail.py "your.email@gmail.com" "abcd1234efgh5678"
```

Expected output:
```
🔍 Testing Gmail configuration for: your.email@gmail.com
============================================================
IMAP Server: imap.gmail.com
IMAP Port: 993
Email: your.email@gmail.com
------------------------------------------------------------

📧 Creating EmailService...
🔐 Attempting to connect to IMAP server...
✅ Connection successful!
📬 Successfully accessed INBOX
✅ Test completed successfully!
```

### Option 3: Using Postman

**Endpoint:** `POST http://localhost:5001/api/email/config`

**Headers:** 
- `Content-Type: application/json`
- `Authorization: Bearer <your_auth_token>`

**Body:**
```json
{
  "email_address": "your.email@gmail.com",
  "email_password": "abcd1234efgh5678",
  "email_provider": "gmail",
  "test_connection": true
}
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Email configuration updated",
  "test_result": "✓ Connection successful",
  "config": {
    "email_address": "your.email@gmail.com",
    "email_provider": "gmail",
    "imap_server": "imap.gmail.com",
    "smtp_server": "smtp.gmail.com"
  }
}
```

---

## Troubleshooting

### "Connection error: IMAP4_SSL" or "ssl.SSLError"
- Verify you're using an **App Password**, not regular password
- Check that 2FA is enabled on your Gmail account

### "Authentication failed" or "Login failed"
- Double-check the app password (copy-paste from Google)
- Verify email address is correct
- Make sure you're not using regular Gmail password

### "Connection refused"
- Check internet connection
- Verify imap.gmail.com is accessible
- Check firewall/proxy settings

### "Port 993 refused"
- Try port 993 with SSL/TLS enabled (default)
- If still fails, Gmail might have specific requirements for your network

### Configuration Changes Not Taking Effect
- Restart the backend: `python run.py`
- Configuration is read from `.env` file on each request

---

## Supported Email Providers

The system now auto-configures these providers:

| Provider | IMAP Server | IMAP Port | SMTP Server | SMTP Port |
|----------|-------------|-----------|-------------|-----------|
| Gmail | imap.gmail.com | 993 | smtp.gmail.com | 587 |
| Outlook | outlook.office365.com | 993 | smtp.office365.com | 587 |
| Yahoo | imap.mail.yahoo.com | 993 | smtp.mail.yahoo.com | 465 |
| iCloud | imap.mail.me.com | 993 | smtp.mail.me.com | 587 |

For other providers, you must manually specify IMAP/SMTP servers.

---

## What Changed in Backend

**File:** `backend/app/api/email_scheduling.py`

### Change 1: Fixed `imap_port` Parameter (Line 605)
```python
# BEFORE
service = EmailService(imap_server, email_address, email_password)

# AFTER  
service = EmailService(imap_server, email_address, email_password, imap_port)
```

### Change 2: Added Default Servers for Providers (Line 577-587)
```python
# Set default IMAP/SMTP servers based on provider if not provided
if not imap_server:
    provider_defaults = {
        'gmail': ('imap.gmail.com', 993, 'smtp.gmail.com', 587),
        'outlook': ('outlook.office365.com', 993, 'smtp.office365.com', 587),
        'yahoo': ('imap.mail.yahoo.com', 993, 'smtp.mail.yahoo.com', 465),
        'icloud': ('imap.mail.me.com', 993, 'smtp.mail.me.com', 587),
    }
    if email_provider in provider_defaults:
        imap_server, imap_port, smtp_server, smtp_port = provider_defaults[email_provider]
```

### Change 3: Better Error Logging (Line 610)
```python
logger.error(f"Test connection failed: {e}", exc_info=True)
```

---

## Next Steps

1. ✅ Restart backend server
2. ✅ Navigate to Settings → Email
3. ✅ Fill in Gmail credentials
4. ✅ Test connection
5. ✅ Load emails from INBOX
6. ✅ Configure auto-reply (optional)
7. ✅ Set up email scheduling (optional)

---

## Security Notes

- ✅ App passwords are more secure than regular passwords
- ✅ Configuration stored in `.env` (not in database)
- ✅ Only admin users can configure email
- ✅ Passwords can be updated anytime via Settings UI
- ✅ IMAP uses SSL/TLS encryption (port 993)
- ✅ SMTP uses TLS encryption (port 587)

---

## Need Help?

If you still encounter issues:

1. Check backend console logs for error messages
2. Verify Gmail account credentials
3. Ensure 2-factor authentication is enabled
4. Generate a new app password from myaccount.google.com/apppasswords
5. Restart the backend server after configuration

