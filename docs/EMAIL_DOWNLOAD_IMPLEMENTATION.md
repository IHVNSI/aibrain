# Email Loading & Download Implementation Guide

## Overview

The email system has been fully implemented to download and store emails from your configured email account into the database.

---

## ✅ What's Implemented

### 1. **Email Download Endpoints**
- `GET /api/email/unread` - Fetch unread emails (stores in database)
- `POST /api/email/sync` - Sync all emails from last N days
- `GET /api/email/list` - List emails stored in database

### 2. **Email Storage**
- `StoredEmail` database table for persistent email storage
- Tracks email UIDs to prevent duplicates
- Stores sender, subject, body, HTML, date, read status

### 3. **Email Configuration**
- IMAP server configuration via `.env`
- Support for Gmail, Outlook, Yahoo, iCloud, and custom servers
- Automatic connection handling with fallback

---

## 🚀 Quick Start: Download Your Emails

### Step 1: Verify Email Configuration
Check your `.env` file has:
```ini
EMAIL_ADDRESS=your-email@domain.com
EMAIL_PASSWORD=your-app-password
EMAIL_IMAP_SERVER=imap.your-provider.com
EMAIL_IMAP_PORT=993
EMAIL_PROVIDER=gmail  # or outlook, yahoo, icloud, custom
```

### Step 2: Download Unread Emails
```bash
curl -X GET "http://localhost:5001/api/email/unread?limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "success": true,
  "emails": [
    {
      "id": "12345",
      "from": "sender@example.com",
      "subject": "Project Update",
      "text": "Here's the latest...",
      "date": "2025-08-14T10:30:00",
      "is_unread": true
    }
  ],
  "count": 5,
  "stored": 3,
  "message": "Retrieved 5 unread emails, stored 3 new"
}
```

### Step 3: Sync All Emails (Last 30 Days)
```bash
curl -X POST "http://localhost:5001/api/email/sync" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"days_back": 30, "limit": 100}'
```

### Step 4: View Stored Emails
```bash
curl -X GET "http://localhost:5001/api/email/list?limit=50&offset=0" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📧 Email Provider Setup

### Gmail
```ini
EMAIL_PROVIDER=gmail
EMAIL_IMAP_SERVER=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-specific-password  # NOT regular password!
```

**Get App-Specific Password:**
1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Enable 2-factor authentication
3. Create app-specific password for "Mail" on "Windows Computer"
4. Use that password in `.env`

### Outlook / Office 365
```ini
EMAIL_PROVIDER=outlook
EMAIL_IMAP_SERVER=outlook.office365.com
EMAIL_IMAP_PORT=993
EMAIL_ADDRESS=your-email@company.com
EMAIL_PASSWORD=your-outlook-password
```

### Yahoo Mail
```ini
EMAIL_PROVIDER=yahoo
EMAIL_IMAP_SERVER=imap.mail.yahoo.com
EMAIL_IMAP_PORT=993
EMAIL_ADDRESS=your-email@yahoo.com
EMAIL_PASSWORD=your-app-specific-password
```

### iCloud
```ini
EMAIL_PROVIDER=icloud
EMAIL_IMAP_SERVER=imap.mail.me.com
EMAIL_IMAP_PORT=993
EMAIL_ADDRESS=your-email@icloud.com
EMAIL_PASSWORD=your-app-specific-password
```

### Custom Mail Server
```ini
EMAIL_PROVIDER=custom
EMAIL_IMAP_SERVER=mail.yourdomain.com
EMAIL_IMAP_PORT=993
EMAIL_ADDRESS=your-email@yourdomain.com
EMAIL_PASSWORD=your-password
```

---

## API Reference

### GET /api/email/unread
Download unread emails and store in database.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 50 | Max emails to fetch |
| folder | string | INBOX | Email folder name |
| store | boolean | true | Store in database |

**Response:**
```json
{
  "success": true,
  "emails": [...],
  "count": 5,
  "stored": 3,
  "message": "Retrieved 5 unread emails, stored 3 new"
}
```

### POST /api/email/sync
Sync all emails from date range to database.

**Request Body:**
```json
{
  "days_back": 30,
  "limit": 100
}
```

**Response:**
```json
{
  "success": true,
  "total_downloaded": 100,
  "total_stored": 45,
  "new_emails": 12,
  "message": "Synced 100 emails, stored 12 new in database"
}
```

### GET /api/email/list
List emails stored in database.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 50 | Max results per page |
| offset | int | 0 | Skip N emails (for pagination) |
| unread_only | boolean | false | Only show unread |

**Response:**
```json
{
  "success": true,
  "emails": [
    {
      "id": 1,
      "email_uid": "12345",
      "from_address": "sender@example.com",
      "subject": "Subject line",
      "body": "Email body...",
      "received_date": "2025-08-14T10:30:00",
      "is_read": false,
      "folder": "INBOX",
      "created_at": "2025-08-14T10:31:00"
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

---

## Troubleshooting

### "Email service not configured"
**Solution:** Check `.env` has `EMAIL_ADDRESS`, `EMAIL_PASSWORD`, `EMAIL_IMAP_SERVER` set.

### "Failed to connect to email server"
**Possible causes:**
1. Wrong password (especially Gmail - must use app-specific password)
2. IMAP not enabled in email account
3. Wrong IMAP server address
4. Firewall blocking port 993

**Solution:**
- For Gmail: [Enable IMAP](https://support.google.com/mail/answer/7126229)
- For Outlook: Use `outlook.office365.com`
- Test with: `telnet your-imap-server 993`

### "Emails retrieved but not showing in app"
**Causes:**
1. UI not calling the endpoint
2. Emails stored but not displayed

**Solution:**
- Check frontend is calling `/api/email/list`
- Check database has StoredEmail table: `sqlite3 brainr.db ".tables"`

### "Only fetching one email at a time"
**Cause:** IMAP connection being closed prematurely.

**Solution:** Already fixed! Improved error handling ensures connection persists.

### "Getting duplicate emails"
**Cause:** Email UIDs not matching due to encoding.

**Solution:** System uses IMAP UID for deduplication automatically. Won't store duplicates.

---

## Database Structure

### StoredEmail Table
```sql
CREATE TABLE stored_emails (
  id INTEGER PRIMARY KEY,
  email_uid VARCHAR(255) UNIQUE NOT NULL,  -- IMAP UID
  from_address VARCHAR(255) NOT NULL,
  subject TEXT NOT NULL,
  body TEXT,
  html_body TEXT,
  received_date DATETIME NOT NULL,
  is_read BOOLEAN DEFAULT 0,
  folder VARCHAR(100) DEFAULT 'INBOX',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## Example Workflow

### Scenario: Download All Emails and Display in Frontend

**Step 1: Sync emails (backend)**
```bash
POST /api/email/sync
Body: {"days_back": 30, "limit": 100}
```
Returns: `{"success": true, "new_emails": 45}`

**Step 2: Fetch emails (frontend)**
```bash
GET /api/email/list?limit=20&offset=0
```
Returns: List of 20 emails

**Step 3: Display in UI**
- Show email sender, subject, date
- Mark read/unread
- Search and filter
- Click to read full body

---

## Advanced Features

### Mark Email as Read
```bash
POST /api/email/mark-read/{email_id}
```

### Search Emails
```bash
GET /api/email/search?query=invoice&limit=10
```

### Get Available Folders
```bash
GET /api/email/folders
```

---

## Security Considerations

1. **Credentials:** Stored in `.env`, never in database
2. **Database:** Emails stored in SQLite locally
3. **API Access:** Requires authentication token
4. **Data Retention:** Configure when/if to delete old emails

---

## Performance Tips

1. **Use Pagination:** Fetch 50 emails at a time, not all at once
2. **Limit Date Range:** Sync last 30 days, not all history
3. **Batch Operations:** Use `/api/email/sync` instead of multiple `/unread` calls
4. **Indexing:** Database indexes on `email_uid` and `received_date` for fast queries

---

## Next Steps

1. **Set up email configuration** in `.env`
2. **Run first sync:** `POST /api/email/sync`
3. **Display in UI:** Create email list view with `/api/email/list`
4. **Add search/filter:** Use email search endpoint
5. **Enable notifications:** Auto-sync periodically and notify user of new emails

---

## Related Documentation
- [Email Configuration Guide](./EMAIL_CONFIGURATION_GUIDE.md)
- [SMTP Sending Setup](./SETUP_EMAIL_AND_SCHEDULER.md)
- [API Usage Guide](./API_Usage.md)

---

**Last Updated:** 2025-01-22
**Status:** ✅ Production Ready
