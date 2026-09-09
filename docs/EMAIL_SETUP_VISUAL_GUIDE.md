# Email Configuration UI - Quick Visual Guide

## What Changed in Settings → Email Tab

### Configuration Section (NEW)

Located at the **top** of the Email tab, before the email list controls:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ⚙️  Email Configuration                                               ▼│
└─────────────────────────────────────────────────────────────────────────┘
```

**Click to expand:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ⚙️  Email Configuration                                               ▲│
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  📧 Email Address                                                        │
│  [____your.email@gmail.com_______________________]                       │
│                                                                           │
│  🔒 Email Password                                                       │
│  [•••••••••••••••••••••••]  👁️                                          │
│  💡 For Gmail: use App Password, not your regular password               │
│                                                                           │
│  Email Provider                                                          │
│  [Gmail] [Outlook] [Yahoo] [iCloud] [Custom]                             │
│   (Auto-fills IMAP/SMTP server details)                                  │
│                                                                           │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                           │
│  📡 IMAP Settings (Reading Emails)                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ IMAP Server              IMAP Port    ☑️ Use TLS/SSL            │   │
│  │ [imap.gmail.com____]     [993___]                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  📡 SMTP Settings (Sending Emails)                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ SMTP Server              SMTP Port    ☑️ Use TLS/SSL            │   │
│  │ [smtp.gmail.com____]     [587___]                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  Advanced Settings                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Check Interval (minutes)    Fetch Limit (emails)               │   │
│  │ [5__]                       [10__]                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  [🧪 Test Connection]  [✓ Save Configuration]                           │
│                                                                           │
│  Test Result (appears after clicking Test Connection):                   │
│  ✓ Connection successful                                                 │
│  or                                                                       │
│  ✗ Connection error: Invalid credentials...                              │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Setup Workflow

### 1️⃣ Select Provider
Click one of: **Gmail**, **Outlook**, **Yahoo**, **iCloud**, or **Custom**

→ IMAP/SMTP servers auto-populate (except for Custom)

### 2️⃣ Enter Email Address
```
Email Address: [your.email@gmail.com]
```

### 3️⃣ Enter Password
```
Email Password: [••••••••••••••] 👁️  ← Click to show/hide password
💡 For Gmail: Use App Password from https://myaccount.google.com/apppasswords
```

### 4️⃣ Review IMAP Settings
```
📡 IMAP Settings (for reading emails)
IMAP Server: [imap.gmail.com]  (auto-filled for Gmail)
IMAP Port:   [993]              (auto-filled)
TLS/SSL:     ☑️  (enabled)
```

### 5️⃣ Review SMTP Settings
```
📡 SMTP Settings (for sending emails)
SMTP Server: [smtp.gmail.com]   (auto-filled for Gmail)
SMTP Port:   [587]              (auto-filled)
TLS/SSL:     ☑️  (enabled)
```

### 6️⃣ Configure Advanced Settings
```
Advanced Settings
Check Interval:  [5] minutes    (How often to auto-check for new emails)
Fetch Limit:     [10] emails    (Max emails to fetch per check)
```

### 7️⃣ Test Connection
```
[🧪 Test Connection]
↓
Wait for result...
↓
✓ Connection successful  →  Proceed to Save
or
✗ Connection error: Invalid credentials  →  Fix and retry
```

### 8️⃣ Save Configuration
```
[✓ Save Configuration]
↓
Configuration saved to .env
↓
Success message: "✓ Email configuration saved successfully"
↓
Configuration panel closes, email features become available
```

---

## What You Can Do After Configuration

### Load Unread Emails
```
Folder: [INBOX ▼]
Load Limit: [10]
[Load Unread]
→ Shows 5 unread emails
```

### Search Emails
```
Search: [keyword_______]  [Search]
→ Shows matching emails
```

### Browse Email Folders
```
Folder: [INBOX ▼]  ← Select different folders
- INBOX
- Sent
- Drafts
- Trash
- Archive
```

### Read Email Details
```
Click on any email → Full email details appear
- From, To, CC, BCC
- Subject
- Date/Time
- Full message body
- HTML version (if available)
```

---

## Common Issues & Solutions

### ❌ "Connection failed"
1. Check email address is correct
2. Check password is correct (Gmail: use App Password)
3. Verify IMAP server address
4. Try enabling/disabling TLS/SSL
5. For Gmail: generate App Password at https://myaccount.google.com/apppasswords

### ❌ "Invalid credentials"
1. Password is case-sensitive - double check capitalization
2. Gmail users: must use App Password, not regular password
3. Yahoo users: use App Password from https://account.yahoo.com/account/security
4. iCloud users: generate App Password at https://appleid.apple.com/account/manage

### ⚠️ No emails appear after saving
1. Check if there are actually unread emails in the folder
2. Verify fetch limit is at least 1
3. Try a different folder
4. Check email provider account settings

---

## Provider-Specific Tips

### 📧 Gmail
- Use **App Password** (not regular password)
- Generate at: https://myaccount.google.com/apppasswords
- IMAP: `imap.gmail.com:993` (TLS/SSL enabled)
- SMTP: `smtp.gmail.com:587` (TLS/SSL enabled)

### 📧 Outlook / Office 365
- Can use regular password or app password
- IMAP: `outlook.office365.com:993` (TLS/SSL enabled)
- SMTP: `smtp.office365.com:587` (TLS/SSL enabled)

### 📧 Yahoo Mail
- Use **App Password** from https://account.yahoo.com/account/security
- IMAP: `imap.mail.yahoo.com:993` (TLS/SSL enabled)
- SMTP: `smtp.mail.yahoo.com:465` (TLS/SSL enabled)

### 📧 iCloud Mail
- Use **App Password** from https://appleid.apple.com/account/manage
- IMAP: `imap.mail.me.com:993` (TLS/SSL enabled)
- SMTP: `smtp.mail.me.com:587` (TLS/SSL enabled)

---

## Security Notes

✅ **Passwords are secure:**
- Stored only in `.env` file (never in database)
- Not displayed in API responses
- Only accessible to administrators
- All connections use TLS/SSL encryption

⚠️ **Best Practices:**
- Never commit `.env` file to Git
- Restrict `.env` file permissions
- Use app-specific passwords when available
- Keep `.env` secure on the server
- Regularly review access logs

---

## Next Steps

1. ✅ Navigate to Settings → Email
2. ✅ Click "Email Configuration" to expand
3. ✅ Select your email provider
4. ✅ Enter email address and app password
5. ✅ Click "Test Connection"
6. ✅ If successful, click "Save Configuration"
7. ✅ Start reading emails!

**Questions?** See [EMAIL_CONFIGURATION_GUIDE.md](./EMAIL_CONFIGURATION_GUIDE.md) for detailed documentation.
