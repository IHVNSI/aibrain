# Live Transcription & Email/Scheduler Feature Testing Guide

## 🎤 Live Transcription Testing (Multi-Chat)

### Test Environment Setup
```
Frontend: http://localhost:5173
Backend: http://localhost:5001
Browser: Chrome/Edge/Safari (Web Speech API required)
```

### Test Case 1: Live Transcription During Recording

**Preconditions:**
- Application is running
- User is logged in and has access to Multi-Person Chat
- Microphone is connected and working

**Steps:**
1. Navigate to Multi-Person Chat page
2. Check "Auto-detect speakers" checkbox
3. Select "English" from Language dropdown
4. Click "Start Recording"

**Expected Results:**
- ✓ Live Transcription panel appears with blue border
- ✓ Microphone icon shows and bounces
- ✓ "ENGLISH" language tag displays
- ✓ "Listening for speech..." message shown initially

**Step 5:** Say something in English (e.g., "Hello, this is a test")

**Expected Results:**
- ✓ Interim text appears in gray italic while speaking
- ✓ Text updates in real-time as you speak
- ✓ No lag between speaking and display

**Step 6:** Pause speaking for 1-2 seconds

**Expected Results:**
- ✓ Interim text becomes final (black, bold)
- ✓ Next speech creates new interim segment
- ✓ Previous text stays in transcript

**Step 7:** Click "Stop Recording"

**Expected Results:**
- ✓ Live Transcription panel disappears
- ✓ Microphone icon stops bouncing
- ✓ Loading indicator shows "Processing audio..."

**Step 8:** Wait for diarization to complete (10-30 seconds)

**Expected Results:**
- ✓ "Detected Speakers" green box appears
- ✓ Conversation transcript shows with speaker name
- ✓ Success message shows: "✓ Detected N speaker(s) and M statement(s)"

---

### Test Case 2: Live Transcription with African Language

**Setup:**
- Same as Test Case 1, but at Step 3, select "Igbo" language

**Steps 1-2:** Same as above

**Step 3:** Select "Igbo" from Language dropdown

**Expected Results:**
- ✓ Language changes to "Igbo"
- ✓ Drop-down shows "Igbo"

**Step 4:** Click "Start Recording"

**Expected Results:**
- ✓ "IGBO" language tag displays in Live Transcription panel

**Step 5:** Speak in Igbo (e.g., "Kedu ka mma")

**Expected Results:**
- ✓ Interim text shows Igbo text/phonetics
- ✓ Real-time updates as you speak
- ✓ Text appears with correct encoding

**Step 6-8:** Same as Test Case 1

**Additional Verification:**
- ✓ If Google Cloud STT configured:
  - Igbo text should appear phonetically accurate
  - Transcription quality should be 3-5x better than Whisper alone
- ✓ If only Whisper available:
  - Igbo may show as phonetics/letters
  - This is expected - recommend enabling Google Cloud STT

---

### Test Case 3: Multiple Language Switching

**Steps:**
1. Start Recording with English
2. Speak in English for 2-3 sentences
3. Stop Recording and wait for diarization
4. Observe:
   - ✓ Transcript shows with English text
   - ✓ If translation enabled, English translation appears
   - ✓ Speaker is detected

**Repeat for Igbo, Hausa, Yoruba languages**

**Expected Results:**
- ✓ Live transcription works for all languages
- ✓ Speaker detection works across languages
- ✓ Transitions between languages are smooth

---

## 📧 Email Feature Testing

### Test Case 1: Email API - Get Unread Emails

**Setup:**
- Backend running at http://localhost:5001
- Valid JWT token from login
- Email configured in .env (EMAIL_ADDRESS, EMAIL_PASSWORD)

**API Call:**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:5001/api/email/unread?limit=5
```

**Expected Response:**
```json
{
  "success": true,
  "emails": [
    {
      "id": "uid-123",
      "from": "sender@example.com",
      "subject": "Test Email",
      "date": "2025-08-14T10:30:00",
      "text": "Email body...",
      "is_unread": true
    }
  ],
  "count": 5
}
```

---

### Test Case 2: Email API - Search Emails

**API Call:**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:5001/api/email/search?q=important&limit=10"
```

**Expected Response:**
- ✓ HTTP 200 OK
- ✓ Returns matching emails
- ✓ count reflects actual number of results

---

### Test Case 3: Email API - List Folders

**API Call:**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:5001/api/email/folders
```

**Expected Response:**
```json
{
  "success": true,
  "folders": ["INBOX", "Sent", "Drafts", "Trash", ...],
  "count": 8
}
```

---

## ⏰ Scheduler Feature Testing

### Test Case 1: Create Scheduled Task

**API Call:**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Morning Email Check",
    "task_type": "email_check",
    "instruction": "read email at 10 AM",
    "description": "Check emails every morning",
    "task_config": {"limit": 10}
  }' \
  http://localhost:5001/api/scheduler/tasks
```

**Expected Response:**
- ✓ HTTP 201 Created
- ✓ Response includes task ID and name
- ✓ Message: "Task 'Morning Email Check' created successfully"

**Verification in Database:**
```sql
SELECT * FROM scheduled_task WHERE name='Morning Email Check';
```

**Expected Results:**
- ✓ Row exists in table
- ✓ `is_active` = 1
- ✓ `schedule_config` contains cron expression
- ✓ `natural_language_instruction` = "read email at 10 AM"

---

### Test Case 2: Natural Language Parsing

**Test Instructions:**
```
"read email at 10 AM" 
→ Cron: "0 10 * * *" (10:00 AM daily)

"every 30 minutes"
→ Interval: 30 minutes

"at 9 AM on Monday"
→ Cron: "0 9 * * 1" (Monday 9 AM)

"every day at 2 PM"
→ Cron: "0 14 * * *" (Daily 2 PM)
```

**API Call (for each instruction):**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "task_type": "email_check", "instruction": "YOUR_INSTRUCTION"}' \
  http://localhost:5001/api/scheduler/tasks
```

**Expected Results:**
- ✓ All instructions accepted without error
- ✓ schedule_config properly parsed to cron/interval
- ✓ Database shows correct schedule

---

### Test Case 3: Get All Tasks

**API Call:**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:5001/api/scheduler/tasks
```

**Expected Response:**
```json
{
  "success": true,
  "tasks": [
    {
      "id": 1,
      "name": "Morning Email Check",
      "task_type": "email_check",
      "is_active": true,
      "last_run": null,
      "next_run": "2025-08-15T10:00:00"
    }
  ],
  "count": 1
}
```

---

### Test Case 4: Start/Stop Scheduler

**Start Scheduler:**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:5001/api/scheduler/start
```

**Expected Response:**
- ✓ HTTP 200 OK
- ✓ Message: "Task scheduler started"

**Verify in Logs:**
- ✓ Look for "APScheduler started" in server logs
- ✓ Check "next_run" updates for created tasks

**Stop Scheduler:**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:5001/api/scheduler/stop
```

**Expected Response:**
- ✓ HTTP 200 OK
- ✓ Message: "Task scheduler stopped"

---

### Test Case 5: Enable/Disable Task

**Disable Task:**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:5001/api/scheduler/tasks/1/disable
```

**Expected Results:**
- ✓ HTTP 200 OK
- ✓ Database shows `is_active` = 0
- ✓ Task no longer runs

**Enable Task:**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:5001/api/scheduler/tasks/1/enable
```

**Expected Results:**
- ✓ HTTP 200 OK
- ✓ Database shows `is_active` = 1
- ✓ Task resumes execution

---

### Test Case 6: Update Task

**API Call:**
```bash
curl -X PUT \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Email Check",
    "instruction": "read email at 11 AM"
  }' \
  http://localhost:5001/api/scheduler/tasks/1
```

**Expected Results:**
- ✓ HTTP 200 OK
- ✓ Task name updated in database
- ✓ Schedule recalculated from new instruction
- ✓ Message: "Task updated successfully"

---

### Test Case 7: Delete Task

**API Call:**
```bash
curl -X DELETE \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:5001/api/scheduler/tasks/1
```

**Expected Results:**
- ✓ HTTP 200 OK
- ✓ Task removed from database
- ✓ Message: "Task deleted successfully"

---

## 🔍 Debug Checklist

### Live Transcription Issues
- [ ] Browser supports Web Speech API (Chrome 70+, Edge 79+)
- [ ] Microphone permissions granted
- [ ] `interimResults: true` in recognition config
- [ ] Language code maps correctly (ig-NG, yo-NG, ha-NG)
- [ ] No errors in browser console (F12 → Console)
- [ ] Server logs show no errors

### Email Issues
- [ ] .env variables set correctly
- [ ] Email provider credentials valid (test with email client first)
- [ ] IMAP access enabled on email account
- [ ] 2FA/app passwords configured if needed
- [ ] No firewall blocking IMAP port 993
- [ ] Server logs show connection success

### Scheduler Issues
- [ ] TaskScheduler initialized successfully
- [ ] APScheduler running without errors
- [ ] Tasks visible in database
- [ ] Natural language parsing working
- [ ] Scheduler started via `/api/scheduler/start`
- [ ] No conflicting cron jobs

---

## 📋 Performance Metrics

### Live Transcription Latency
- Interim update: < 100ms from speech to display
- Final update: < 500ms after user pauses
- Language switching: < 50ms
- Diarization: 10-30 seconds for 1-2 minutes audio

### Email Performance
- List unread (10 emails): < 2 seconds
- Search (50 emails): < 3 seconds
- Mark as read: < 1 second
- Get folders: < 1 second

### Scheduler Performance
- Create task: < 100ms
- List tasks (10 tasks): < 500ms
- Update task: < 100ms
- Delete task: < 100ms
- Start scheduler: < 2 seconds

---

## ✅ Pass/Fail Criteria

**Feature is Ready When:**
1. ✓ Live transcription displays interim text within 100ms
2. ✓ Multi-language support works (English, Igbo, Hausa, Yoruba)
3. ✓ Batch diarization completes without errors
4. ✓ All 4 email endpoints respond with HTTP 200
5. ✓ All 8 scheduler endpoints respond correctly
6. ✓ Natural language parsing works for time/interval formats
7. ✓ Tasks persist in database
8. ✓ No authentication errors (except missing/invalid tokens)
9. ✓ No console errors or warnings
10. ✓ Database tables created automatically

---

## 🎯 Known Limitations

1. **Live Transcription:**
   - Limited to single audio stream (doesn't separate speakers in real-time)
   - Batch diarization needed to identify multiple speakers
   - Some African languages may show as phonetics without Google Cloud STT

2. **Email:**
   - Only reads unread emails (threaded conversations not yet supported)
   - No attachment handling in current implementation
   - Auto-response not yet implemented

3. **Scheduler:**
   - Event triggers (on new email) not yet implemented
   - Task retry logic not yet implemented
   - No email notifications for task completion

---

## 📞 Support Information

For test failures, check:
1. **Server logs:** `logs/` directory
2. **Browser console:** F12 → Console tab
3. **Database:** Check SQLite tables exist and have data
4. **Configuration:** Verify .env variables are set
5. **Network:** Ensure backend/frontend can communicate
