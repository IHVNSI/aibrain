# Email Auto-Check Scheduling - Implementation Guide

## Overview

The Brainr email system now automatically checks for new emails at a configurable interval. By default, it checks every **5 minutes** (as set in `EMAIL_CHECK_INTERVAL`).

---

## How It Works

### On Startup
1. ✅ Backend starts and initializes the Flask app
2. ✅ `setup_email_scheduler()` is called during app initialization
3. ✅ Task scheduler is created and started
4. ✅ Email handlers are initialized (email_check, email_respond)
5. ✅ "Automatic Email Check" task is created with EMAIL_CHECK_INTERVAL
6. ✅ Scheduler begins polling for emails at the set interval

### Every 5 Minutes (by default)
1. ✅ Email check task runs automatically
2. ✅ Connects to configured IMAP server
3. ✅ Fetches up to 20 unread emails from INBOX
4. ✅ Stores new emails in database (StoredEmail table)
5. ✅ Disconnects and logs result
6. ✅ Next check scheduled for 5 minutes later

---

## Configuration

### Default Setting
```bash
EMAIL_CHECK_INTERVAL=5    # Check every 5 minutes
```

### Change via Environment Variable
Edit `.env` file:
```bash
EMAIL_CHECK_INTERVAL=10   # Check every 10 minutes
EMAIL_CHECK_INTERVAL=1    # Check every 1 minute (frequent)
EMAIL_CHECK_INTERVAL=60   # Check every 1 hour
```

### Change via API (Dynamic)

**GET current interval:**
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:5001/api/email/check-interval
```

**Response:**
```json
{
  "success": true,
  "check_interval": 5,
  "unit": "minutes",
  "task": {
    "id": 1,
    "name": "Automatic Email Check",
    "is_active": true,
    "last_run": "2024-09-22T10:30:00",
    "next_run": "2024-09-22T10:35:00"
  }
}
```

**UPDATE interval:**
```bash
curl -X POST -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"check_interval": 10}' \
  http://localhost:5001/api/email/check-interval
```

**Response:**
```json
{
  "success": true,
  "message": "Email check interval updated to 10 minutes",
  "check_interval": 10
}
```

### Validation
- Minimum: 1 minute
- Maximum: 1440 minutes (24 hours)
- Default: 5 minutes

---

## Scheduler Architecture

### Components

**1. TaskScheduler (scheduler_service.py)**
- Manages background task scheduling using APScheduler
- Supports cron and interval-based triggers
- Loads tasks from database
- Provides API for creating/updating/deleting tasks

**2. Email Handlers (email_scheduling.py)**
- `handle_email_check()`: Fetches unread emails
- `handle_email_respond()`: Generates AI responses (optional)

**3. Setup Function (email_scheduling.py)**
- `setup_email_scheduler()`: Runs on app startup
- Creates automatic email check task
- Initializes handlers
- Starts scheduler

### Flow Diagram

```
App Startup
    ↓
setup_email_scheduler()
    ↓
Create TaskScheduler instance
    ↓
Initialize email_check handler
    ↓
Create "Automatic Email Check" task
├─ Type: interval
├─ Interval: EMAIL_CHECK_INTERVAL (5 min default)
├─ Handler: handle_email_check()
└─ Config: limit=20, folder=INBOX
    ↓
scheduler.start()
    ↓
Every 5 minutes:
├─ EmailConfig.get_email_service()
├─ email_service.get_unread_emails(limit=20)
├─ Store emails in database
├─ Disconnect
└─ Log completion
```

---

## Monitoring Email Checks

### Check Logs
Backend logs show:
```
✓ Email check completed: 3 unread emails
✓ Task completed: Automatic Email Check
```

### View Scheduled Tasks
```bash
GET /api/scheduler/tasks
```

**Response:**
```json
{
  "success": true,
  "tasks": [
    {
      "id": 1,
      "name": "Automatic Email Check",
      "task_type": "email_check",
      "is_active": true,
      "last_run": "2024-09-22T10:30:00Z",
      "next_run": "2024-09-22T10:35:00Z",
      "schedule_config": {
        "type": "interval",
        "minutes": 5
      }
    }
  ]
}
```

### View Last Email Check
The `last_run` and `next_run` times show when the check last executed and when it will run next.

---

## Database Tables

### scheduled_tasks Table
```sql
CREATE TABLE scheduled_tasks (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    task_type VARCHAR(50),           -- 'email_check', 'email_respond', etc.
    schedule_config TEXT,             -- JSON: {"type": "interval", "minutes": 5}
    task_config TEXT,                 -- JSON: {"limit": 20, "folder": "INBOX"}
    is_active BOOLEAN DEFAULT true,
    last_run DATETIME,
    next_run DATETIME,
    created_at DATETIME,
    updated_at DATETIME
);
```

### StoredEmail Table
```sql
CREATE TABLE stored_emails (
    id INTEGER PRIMARY KEY,
    folder VARCHAR(100),
    from_address VARCHAR(255),
    subject TEXT,
    body TEXT,
    html_body TEXT,
    received_at DATETIME,
    created_at DATETIME
);
```

---

## Troubleshooting

### Emails Not Auto-Checking

**Check 1: Is email configured?**
```bash
GET /api/email/config
```
Should return EMAIL_ADDRESS and other settings.

**Check 2: Is scheduler running?**
```bash
GET /api/scheduler/tasks
```
Should show "Automatic Email Check" task as active.

**Check 3: Check backend logs**
Look for:
- `✓ Email scheduler started`
- `✓ Created automatic email check task`
- `✓ Email check completed: X unread emails`

**Check 4: Is database working?**
- Verify database connection
- Check if `scheduled_tasks` table exists
- Check if `stored_emails` table exists

### Task Stuck or Not Running

**Solution 1: Restart backend**
```bash
cd backend
python run.py
```

**Solution 2: Check interval is valid**
- Must be 1-1440 minutes
- Default is 5 minutes

**Solution 3: Check email service configuration**
- Verify IMAP server, port, credentials
- Test connection in Settings → Email

### Change Interval Not Taking Effect

**Immediate effect with API:**
```bash
curl -X POST -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"check_interval": 10}' \
  http://localhost:5001/api/email/check-interval
```

**Or restart backend:**
```bash
python run.py
```

---

## Performance Considerations

### Default: 5 Minutes
- ✅ Reasonable update frequency
- ✅ Low server load
- ✅ Good for most use cases

### More Frequent (1-2 minutes)
- ✅ Faster email notifications
- ⚠️ Higher server load
- ⚠️ More database writes

### Less Frequent (30-60 minutes)
- ✅ Lower server load
- ✅ Lower database writes
- ⚠️ Delayed email notifications

### Recommendation
- **5-10 minutes**: Standard use case
- **1 minute**: High-priority email handling
- **30+ minutes**: Low-traffic or resource-constrained systems

---

## Code Changes Summary

### Files Modified

**1. backend/app/api/email_scheduling.py**
- Added `setup_email_scheduler()` function
- Added `GET /api/email/check-interval` endpoint
- Added `POST /api/email/check-interval` endpoint

**2. backend/app/__init__.py**
- Added `setup_email_scheduler` import
- Call `setup_email_scheduler()` during app initialization

### Key Functions

```python
# Initialize and start email checking on app startup
setup_email_scheduler()

# Get current check interval
GET /api/email/check-interval

# Update check interval dynamically
POST /api/email/check-interval
  {"check_interval": 10}
```

---

## Example Scenarios

### Scenario 1: Default Setup
```
1. App starts
2. EMAIL_CHECK_INTERVAL = 5 (from .env)
3. Automatic Email Check task created (every 5 min)
4. Scheduler starts
5. First check runs immediately
6. Subsequent checks run every 5 minutes
```

### Scenario 2: User Changes Interval
```
1. User goes to Settings (future UI)
2. Changes "Email Check Interval" to 10 minutes
3. Sends POST to /api/email/check-interval
4. .env file updated to EMAIL_CHECK_INTERVAL=10
5. Scheduled task updated
6. Next check runs 10 minutes from now
7. Future checks continue every 10 minutes
```

### Scenario 3: Email Arrives
```
1. New email arrives in INBOX
2. During next scheduled check, email is fetched
3. Email stored in StoredEmail table
4. App notifies user (future notification feature)
5. User can read email in Email tab
```

---

## Future Enhancements

- [ ] UI in Settings to change email check interval
- [ ] Email arrival notifications (desktop, mobile)
- [ ] Custom folder monitoring (not just INBOX)
- [ ] Email filtering by sender, subject
- [ ] Automatic archiving old emails
- [ ] Auto-response based on training data
- [ ] Multi-email account support
- [ ] Email forwarding rules

---

## Summary

✅ **Automatic email checking is now active**
- Runs every 5 minutes by default
- Configurable via EMAIL_CHECK_INTERVAL
- Can be changed dynamically via API
- Stores emails in database
- Ready for notifications and workflows
