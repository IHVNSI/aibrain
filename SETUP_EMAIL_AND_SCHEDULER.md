# Email and Scheduler Feature Setup Guide

This guide walks through setting up the new email monitoring and task scheduling features in the Brainr application.

## ✅ Completed Implementation

### Backend Components
- ✅ **EmailService** (`backend/app/email_service.py`) - IMAP email client
- ✅ **TaskScheduler** (`backend/app/scheduler_service.py`) - APScheduler wrapper
- ✅ **API Endpoints** (`backend/app/api/email_scheduling.py`) - 10 REST endpoints
- ✅ **Database Model** - ScheduledTask table for persisting tasks
- ✅ **Flask Integration** - Blueprints registered in app initialization

### Frontend Components  
- ✅ **Live Transcription** - Real-time speech-to-text during Multi-Chat recording
- 🔄 **Email Tab UI** - Not yet implemented
- 🔄 **Scheduler/Admin Tab UI** - Not yet implemented

## 🚀 Step 1: Environment Configuration

### 1.1 Email Service Setup

Add these variables to your `.env` file:

```bash
# Email Configuration
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-specific-password
EMAIL_PROVIDER=gmail
# EMAIL_IMAP_SERVER=imap.gmail.com  # Optional: for custom providers

# For Outlook/Microsoft:
# EMAIL_PROVIDER=outlook
# EMAIL_ADDRESS=your-email@outlook.com

# For Yahoo:
# EMAIL_PROVIDER=yahoo

# For iCloud:
# EMAIL_PROVIDER=icloud
```

### 1.2 Email Provider Setup Instructions

**Gmail:**
1. Enable 2-Factor Authentication on your Google Account
2. Generate an "App Password" at https://myaccount.google.com/apppasswords
3. Use the 16-character password in `EMAIL_PASSWORD`

**Outlook:**
1. Use your regular Outlook password
2. Set `EMAIL_PROVIDER=outlook`

**Yahoo:**
1. Generate an "App Password" at https://login.yahoo.com/
2. Set `EMAIL_PROVIDER=yahoo`

**iCloud:**
1. Generate an "App-specific password" at https://appleid.apple.com/account/manage
2. Set `EMAIL_PROVIDER=icloud`

### 1.3 Google Cloud Speech-to-Text (Optional but Recommended)

For better African language support (Igbo, Yoruba, Hausa):

```bash
# Add to .env:
GOOGLE_CLOUD_STT_CREDENTIALS_PATH=/path/to/credentials.json
```

**Get Credentials:**
1. Create a Google Cloud project
2. Enable Speech-to-Text API
3. Create a service account and download JSON key
4. Set the path in the env variable above

## 🔌 Step 2: Start the Application

### Option A: Using Docker Compose (Recommended)
```bash
cd brainr
docker-compose up --build
```

### Option B: Manual Setup

**Backend:**
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
python run.py
# Server starts at http://localhost:5001
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
# App opens at http://localhost:5173
```

## 📧 Step 3: Email Feature Usage

### Access Email API Endpoints

**Get Unread Emails:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5001/api/email/unread?limit=10&folder=INBOX
```

**Search Emails:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5001/api/email/search?q=important&limit=10
```

**Mark as Read:**
```bash
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5001/api/email/mark-read/<email_id>
```

**List Folders:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5001/api/email/folders
```

### Frontend Email Tab (To Be Implemented)

The email feature will be accessible from a new "📧 Emails" tab in Settings with:
- List of unread emails with previews
- Search functionality
- Email detail view
- Mark as read/unread actions

## ⏰ Step 4: Scheduler Feature Usage

### Create a Scheduled Task

**Via API:**
```bash
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Check emails daily",
    "task_type": "email_check",
    "instruction": "read email at 10 AM",
    "description": "Check for new emails every morning at 10 AM",
    "task_config": {
      "email_folder": "INBOX",
      "limit": 10
    }
  }' \
  http://localhost:5001/api/scheduler/tasks
```

### Natural Language Instructions

The scheduler supports natural language instructions. Examples:

```
"read email at 10 AM"           → Runs daily at 10:00 AM
"check emails every 30 minutes" → Runs every 30 minutes
"read email at 9 AM on Monday"  → Runs at 9 AM every Monday
"whenever new email arrives"    → Runs on event trigger (planned)
```

### Scheduler API Endpoints

**List Tasks:**
```bash
GET /api/scheduler/tasks
```

**Create Task:**
```bash
POST /api/scheduler/tasks
Body: {name, task_type, instruction, description, task_config}
```

**Update Task:**
```bash
PUT /api/scheduler/tasks/<task_id>
Body: {name, instruction, is_active, description}
```

**Delete Task:**
```bash
DELETE /api/scheduler/tasks/<task_id>
```

**Enable/Disable Task:**
```bash
POST /api/scheduler/tasks/<task_id>/enable
POST /api/scheduler/tasks/<task_id>/disable
```

**Start/Stop Scheduler:**
```bash
POST /api/scheduler/start
POST /api/scheduler/stop
```

### Scheduler Admin Tab (To Be Implemented)

The scheduler will be accessible from a new "⏰ Admin" tab in Settings with:
- List of all scheduled tasks
- Create new task form (with natural language instruction field)
- Edit/delete existing tasks
- Task status display (next run, last run, is_active)
- Enable/disable toggle for each task

## 🎤 Step 5: Live Transcription Testing

### Test Multi-Chat with Live Transcription

1. Go to **Multi-Person Chat** page
2. Check "Auto-detect speakers" checkbox
3. Select audio language (English, Igbo, Hausa, Yoruba)
4. Click "Start Recording"
5. Observe:
   - ✓ "Live Transcription" panel appears
   - ✓ Text shows in real-time as you speak
   - ✓ Language tag shows selected language
   - ✓ Interim results display while speaking
   - ✓ Final results accumulate after each pause
6. Click "Stop Recording" when done
7. Wait for diarization to complete
8. Verified speakers and transcripts appear below

### Expected Behavior

**Before Recording:** 
- "Start Recording" button enabled
- Upload file option available

**During Recording:**
- "Live Transcription" panel shows interim text in blue
- Microphone icon bounces
- Real-time updates as user speaks
- Language selector shows current language

**After Recording:**
- Diarization processes the audio
- Detected speakers appear in green box
- Conversation transcript shows speaker segments
- Translation toggle appears if multilingual

## 📊 Database Tables

The scheduler creates these tables automatically:

### ScheduledTask Table
```sql
CREATE TABLE scheduled_task (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    task_type VARCHAR(50) NOT NULL,
    natural_language_instruction TEXT,
    schedule_config JSON NOT NULL,
    task_config JSON,
    is_active BOOLEAN DEFAULT TRUE,
    last_run DATETIME,
    next_run DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER
);
```

## 🔐 Security Considerations

1. **Email Credentials**: Never commit `.env` files with real credentials to version control
2. **API Authentication**: All endpoints require valid JWT token (Bearer token in Authorization header)
3. **Task Isolation**: Tasks run with admin privileges but log all actions
4. **Email Privacy**: Email content is not logged or stored permanently

## 🐛 Troubleshooting

### Email Connection Fails
- Verify email/password are correct
- Check if 2FA/app passwords are enabled
- Ensure IMAP access is enabled in email provider settings
- Check firewall rules for IMAP port (usually 993)

### Scheduler Tasks Not Running
- Verify scheduler is started (`POST /api/scheduler/start`)
- Check task is enabled (`is_active = true`)
- Review database to confirm task was created
- Check application logs for task execution errors

### Live Transcription Not Working
- Verify browser supports Web Speech API (Chrome, Edge, Safari recommended)
- Check microphone permissions are granted
- Ensure `interimResults: true` is set in recognition config
- Try different language selection

### Africa Language Recognition Issues
- Ensure Google Cloud STT is configured (better accuracy than Whisper)
- Check language code is correctly mapped (ig-NG, yo-NG, ha-NG)
- For Whisper, use language codes: ig, yo, ha (ISO 639-1)
- Test with clear audio in native language

## 📝 File Structure

**New/Modified Files:**
```
backend/
  app/
    api/
      email_scheduling.py          # NEW: Email + Scheduler API endpoints
    email_service.py               # NEW: IMAP email client
    scheduler_service.py           # NEW: APScheduler wrapper
    models.py                      # MODIFIED: Added ScheduledTask model
    __init__.py                    # MODIFIED: Registered blueprints

frontend/
  src/
    pages/
      MultiPersonChat.jsx          # MODIFIED: Added live transcription

Configuration Files:
  .env                             # MODIFIED: Email/scheduler config
  backend/requirements.txt         # MODIFIED: New dependencies
  docker-compose.yml               # MODIFIED: Environment variables
```

## ✅ Verification Checklist

- [ ] `.env` file configured with email settings
- [ ] Backend dependencies installed (`pip install -r requirements.txt`)
- [ ] Application starts without errors
- [ ] Email endpoints accessible via API
- [ ] Scheduler endpoints accessible via API
- [ ] Multi-Chat shows live transcription while recording
- [ ] Database tables created (check `brainr.db`)
- [ ] No errors in browser console or server logs

## 🎯 Next Steps (Frontend Implementation)

1. Create Email Tab Component
   - Display unread emails list
   - Search functionality
   - Mark as read/unread

2. Create Scheduler/Admin Tab Component
   - Task list with status
   - Create task form
   - Edit/delete task actions
   - Enable/disable toggle

3. Implement Email Response Automation
   - LLM-based auto-reply generation
   - SMTP configuration for sending

4. Integration Testing
   - End-to-end workflow testing
   - Multi-language transcription testing
   - Email monitoring and response

## 📚 Related Documentation

- [AI Context Guide](docs/AI_CONTEXT_GUIDE.md)
- [API Usage Guide](docs/API_Usage.md)
- [How to Configure the App](docs/How_to_Configure_the_App.md)
- [POSTMAN API Testing Guide](docs/POSTMAN_API_TESTING_GUIDE.md)

## 📞 Support

For issues or questions:
1. Check application logs: `logs/` directory
2. Review error messages in browser console (F12)
3. Verify environment configuration
4. Test individual API endpoints manually
