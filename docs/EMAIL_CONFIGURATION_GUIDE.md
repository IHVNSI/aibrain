# Email Configuration Guide

## Overview

The brainr application now includes a complete email management system that allows administrators to configure email settings through the web interface. This guide walks through setting up email reading and sending capabilities.

## Features

- 📧 **Read Emails**: Automatically fetch and manage emails from your email account
- 📤 **Send Emails**: Send emails on behalf of the configured email address
- 🔄 **Auto-Check**: Automatically check for new emails at configurable intervals
- 🔐 **Secure**: Supports encrypted IMAP/SMTP connections with TLS/SSL
- 🧪 **Test Connection**: Verify email configuration before saving
- 🎛️ **Provider Presets**: Quick setup for Gmail, Outlook, Yahoo, iCloud

## Supported Email Providers

### Gmail
- **IMAP Server**: `imap.gmail.com` (Port 993)
- **SMTP Server**: `smtp.gmail.com` (Port 587)
- **Authentication**: App-specific password (recommended)
  - Generate at: https://myaccount.google.com/apppasswords
- **Security**: TLS/SSL enabled by default

### Outlook / Office 365
- **IMAP Server**: `outlook.office365.com` (Port 993)
- **SMTP Server**: `smtp.office365.com` (Port 587)
- **Authentication**: Your Outlook password or app password
- **Security**: TLS/SSL enabled by default

### Yahoo Mail
- **IMAP Server**: `imap.mail.yahoo.com` (Port 993)
- **SMTP Server**: `smtp.mail.yahoo.com` (Port 465)
- **Authentication**: App-specific password (recommended)
  - Generate at: https://account.yahoo.com/account/security
- **Security**: TLS/SSL enabled by default

### iCloud Mail
- **IMAP Server**: `imap.mail.me.com` (Port 993)
- **SMTP Server**: `smtp.mail.me.com` (Port 587)
- **Authentication**: App-specific password
  - Generate at: https://appleid.apple.com/account/manage
- **Security**: TLS/SSL enabled by default

### Custom Email Provider
For other email providers, enter your provider's IMAP and SMTP server details manually.

## Configuration Steps

### Step 1: Access Email Settings
1. Log in as an Administrator
2. Go to **Settings** → **Email** tab
3. Click "Email Configuration" to expand the configuration panel

### Step 2: Enter Basic Information
1. **Email Address**: Enter your full email address (e.g., `info@brainr.com`)
2. **Email Password**: Enter your password or app-specific password
   - 💡 For Gmail: Use an [App Password](https://myaccount.google.com/apppasswords), not your regular password
   - 💡 For Outlook: You can use your regular password or app-specific password
   - 💡 For Yahoo: Use an [App Password](https://account.yahoo.com/account/security)

### Step 3: Select Email Provider
Choose from the predefined providers to auto-populate IMAP/SMTP settings:
- Gmail
- Outlook
- Yahoo
- iCloud
- Custom (for other providers)

### Step 4: Configure IMAP Settings (Optional)
If you selected a preset provider, these are auto-filled:
- **IMAP Server**: Address of your email provider's IMAP server
- **IMAP Port**: Usually 993 for encrypted connections
- **Use TLS/SSL**: Enable for secure connections (recommended)

### Step 5: Configure SMTP Settings (Optional)
If you selected a preset provider, these are auto-filled:
- **SMTP Server**: Address of your email provider's SMTP server
- **SMTP Port**: Usually 587 for TLS or 465 for SSL
- **Use TLS/SSL**: Enable for secure connections (recommended)

### Step 6: Advanced Settings (Optional)
- **Check Interval**: How often to check for new emails (in minutes, default: 5)
- **Fetch Limit**: Maximum emails to fetch per check (default: 10)

### Step 7: Test Connection
1. Click **Test Connection** button
2. Wait for the connection test result
   - ✓ Success: Configuration is valid
   - ✗ Error: Check error message and adjust settings

### Step 8: Save Configuration
1. Once testing is successful, click **Save Configuration**
2. Configuration will be saved and emails will be accessible

## Environment Variables

Email configuration is stored in `.env` file with these variables:

```env
# Basic Settings
EMAIL_ADDRESS=your.email@gmail.com
EMAIL_PASSWORD=your-app-password-or-password
EMAIL_PROVIDER=gmail

# IMAP Settings (Reading Emails)
EMAIL_IMAP_SERVER=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_IMAP_TLS=true

# SMTP Settings (Sending Emails)
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_TLS=true

# Advanced Settings
EMAIL_CHECK_INTERVAL=5
EMAIL_FETCH_LIMIT=10
```

## Common Setup Examples

### Gmail Setup
```
Email Address: your.email@gmail.com
Email Password: [Your App Password from https://myaccount.google.com/apppasswords]
Email Provider: Gmail (preset)
- IMAP Server will auto-fill: imap.gmail.com (Port 993)
- SMTP Server will auto-fill: smtp.gmail.com (Port 587)
```

**Note**: If you see authentication errors:
1. Enable "Less secure app access": https://myaccount.google.com/security
2. Or better: Generate an App Password (recommended)

### Outlook Setup
```
Email Address: your.email@outlook.com
Email Password: Your Outlook password
Email Provider: Outlook (preset)
- IMAP Server will auto-fill: outlook.office365.com (Port 993)
- SMTP Server will auto-fill: smtp.office365.com (Port 587)
```

### Yahoo Mail Setup
```
Email Address: your.email@yahoo.com
Email Password: [Your App Password from https://account.yahoo.com/account/security]
Email Provider: Yahoo (preset)
- IMAP Server will auto-fill: imap.mail.yahoo.com (Port 993)
- SMTP Server will auto-fill: smtp.mail.yahoo.com (Port 465)
```

## Email Management Features

### Reading Emails
Once configured, you can:
- **Load Unread Emails**: Fetch all unread messages
- **Search Emails**: Find emails by subject, sender, or content
- **Browse Folders**: Select different email folders (INBOX, Sent, Drafts, etc.)
- **View Details**: Click on an email to read the full content
- **Mark as Read**: Mark emails as read from the interface

### Auto-Email Checking
The system can automatically:
- Check for new emails at the configured interval
- Fetch the specified number of emails per check
- Enable AI to automatically respond to emails based on rules
- Schedule email tasks for specific times

## Troubleshooting

### Connection Test Failed

**Error: "Connection failed"**
- Verify email address and password are correct
- Check IMAP server address
- Ensure port number is correct (usually 993 for IMAP)
- Try enabling/disabling TLS/SSL
- For Gmail: Use App Password instead of regular password

**Error: "SSL certificate verify failed"**
- This is usually a system certificate issue
- Try disabling TLS/SSL and using port 143 instead
- Or ensure Python certificates are up to date

### Emails Not Loading

**Issue: "Email service not configured"**
- Configuration hasn't been saved yet
- Click "Save Configuration" after entering all details

**Issue: No emails appear**
- Check if there are actually unread emails in the folder
- Verify "Fetch Limit" is set to a reasonable number (at least 1)
- Try a different folder from the dropdown

### Password Issues

**Error: "Invalid credentials"**
- Double-check password is correct (case-sensitive)
- For Gmail/Yahoo: Use App Password, not your regular password
- Some providers require special characters to be escaped

**Issue: Account locked after multiple attempts**
- Some providers lock accounts after failed login attempts
- Wait 24 hours or unlock the account in provider settings
- Then try again with correct password

## API Endpoints

### Get Email Configuration
```
GET /api/email/config
Response: {
  "success": true,
  "config": {
    "email_address": "info@brainr.com",
    "email_provider": "gmail",
    "imap_server": "imap.gmail.com",
    "imap_port": 993,
    "imap_tls": true,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_tls": true,
    "check_interval": 5,
    "fetch_limit": 10,
    "password_configured": true
  },
  "providers": {
    "gmail": { ... },
    "outlook": { ... },
    ...
  }
}
```

### Update Email Configuration
```
POST /api/email/config
Body: {
  "email_address": "info@brainr.com",
  "email_password": "password",
  "email_provider": "gmail",
  "imap_server": "imap.gmail.com",
  "imap_port": 993,
  "imap_tls": true,
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_tls": true,
  "check_interval": 5,
  "fetch_limit": 10,
  "test_connection": false
}
```

### Get Unread Emails
```
GET /api/email/unread?limit=10&folder=INBOX
Response: {
  "success": true,
  "emails": [
    {
      "id": "email_uid",
      "from": "sender@example.com",
      "subject": "Email Subject",
      "text": "Email body...",
      "date": "2025-08-31T10:30:00",
      "is_unread": true
    }
  ],
  "count": 5
}
```

### Search Emails
```
GET /api/email/search?q=keyword&limit=20
Response: {
  "success": true,
  "emails": [ ... ],
  "count": 3
}
```

### Get Email Folders
```
GET /api/email/folders
Response: {
  "success": true,
  "folders": ["INBOX", "Sent", "Drafts", "Trash", ...],
  "count": 7
}
```

## Security Considerations

### Password Storage
- Passwords are stored in `.env` file only
- Never commit `.env` to version control
- Keep `.env` file permissions restricted
- Consider using Docker secrets for production

### Encryption
- All IMAP connections use TLS/SSL (port 993)
- All SMTP connections use TLS/SSL (port 587) or explicit STARTTLS
- Passwords are not stored in database, only in `.env`

### Authentication
- Admin-only access to email configuration
- Role-based access control for email operations
- Audit logging of all email configuration changes

## Performance Optimization

### Email Checking
- Default interval is 5 minutes (configurable)
- Each check fetches up to 10 emails (configurable)
- Increase fetch limit for large mailboxes
- Decrease check interval for more responsive updates

### Database Impact
- Email UIDs are cached locally
- Prevents duplicate processing
- Automatic cleanup of old cached entries

## Support & Resources

- **Email Provider Setup Guides**:
  - Gmail: https://support.google.com/mail/answer/7126229
  - Outlook: https://support.microsoft.com/en-us/office/pop-imap-and-smtp-settings-8361e398-8af4-4e97-b678-c6b6d25d8c7a
  - Yahoo: https://help.yahoo.com/kb/SLN4075.html
  - iCloud: https://support.apple.com/en-us/HT202304

- **Troubleshooting**:
  - Check provider's app password requirements
  - Verify firewall allows connections to IMAP/SMTP ports
  - Test with another email client if possible

## Version History

### v1.0 (Current)
- ✅ Email configuration UI with provider presets
- ✅ IMAP email reading
- ✅ SMTP email sending
- ✅ Connection testing
- ✅ Auto-check scheduling
- ✅ Email search and filtering
- ✅ Folder browsing

### Planned Features
- 📋 Email forwarding rules
- 🔄 Email synchronization
- 📎 Attachment handling
- 🤖 AI-powered email responses
- 📊 Email analytics
