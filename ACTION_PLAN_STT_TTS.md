# 🚀 ACTION PLAN: Complete STT/TTS Setup

## ✅ Completed (Just Now)
- [x] Fixed automatic translation issue
- [x] Removed mock transcript fallback  
- [x] Added optional post-processing translation
- [x] Updated frontend to display original language
- [x] Created new `/translate-conversation` endpoint
- [x] Code validated (0 errors)

## 📋 YOUR ACTION ITEMS (Next Steps)

### PRIORITY 1: Fix ElevenLabs API Key (Blocking TTS)

**Current Status:** ❌ API key missing permissions

**Your Task:**
```
1. Go to: https://elevenlabs.io/app/settings/api-keys
2. Create NEW API key named "brainr-full"
3. Enable permissions:
   ✅ voices_read
   ✅ text_to_speech_create
   ✅ audio_to_text_create
4. Copy the new key
```

**Update .env:**
```bash
# FILE: backend/.env
# Line 77 - REPLACE:
ELEVENLABS_API_KEY=sk_fb23324f9de6b96e8e6ef5c3d0f5aad8e34e563a3c6577da

# WITH NEW KEY:
ELEVENLABS_API_KEY=sk_xxxxxxxxxxxx_your_new_key_xxxxxxxxxxxx
```

**Restart Backend:**
```bash
cd backend
# Stop (Ctrl+C if running)
python run.py
```

---

### PRIORITY 2: Test STT (Speech-to-Text) - Should Work Now

**What Changed:**
- ✅ Original language text displayed in real-time
- ✅ No automatic translation to English
- ✅ Mock transcripts removed

**How to Test:**
```
1. Open app in browser
2. Go to "Multi-Person Chat" tab
3. Select Language: "Igbo" (or Hausa/Yoruba)
4. Click "Start Recording"
5. Speak: "Kedu? Mma onwe gị?" (How are you?)
6. Click "Stop Recording"
7. See: Original Igbo text displayed (NOT English)
```

**Expected Output:**
```
✅ Speaker 1: "Kedu? Mma onwe gị?"  [IGBO language badge]
   (Real text, NOT "Hello? How are you?")
```

**If You See Errors:**
```
❌ Backend error: "ALL STT SERVICES FAILED for 'igbo'"
   Solution: pip install transformers torch librosa
```

---

### PRIORITY 3: Test TTS (Text-to-Speech) - After API Key Fix

**Prerequisites:**
- [ ] New ElevenLabs API key generated with permissions
- [ ] .env file updated
- [ ] Backend restarted
- [ ] Browser refreshed (Ctrl+F5)

**How to Test:**
```
1. Go to Settings → Audio tab
2. Look for "Audio Configuration" section
3. Select Language dropdown: Choose "Igbo"
4. Click "Test TTS" button
5. Listen for greeting in Igbo language
```

**Expected Output:**
```
🔊 Audio plays greeting in Igbo
✓ Status shows: "ElevenLabs Text-to-Speech working"
```

**Greetings by Language:**
| Language | Greeting Will Be |
|----------|------------------|
| Igbo | Igbo language greeting |
| Yoruba | Yoruba language greeting |
| Hausa | Hausa language greeting |
| English | English greeting |
| Pidgin | Pidgin greeting |

---

### PRIORITY 4: Test Optional Translation (After Recording)

**When:** Only available after recording a conversation

**How to Use:**
```
1. Record conversation in Igbo
2. After recording, see blue "🌐 Translate to English" button
3. Click it
4. See: Both original Igbo AND English translation
5. Can toggle between them
```

**Expected UI:**
```
Speaker 1: "Kedu?"  [IGBO badge]
🌐 Translate to English  ← Click this

After clicking:
Speaker 1: "Kedu?"
📝 Auto-Translated:
   "Hello?"
```

---

## 🧪 Complete Test Checklist

### STT (Speech-to-Text) Testing
- [ ] Select "Igbo" language
- [ ] Record audio with Igbo speech
- [ ] Original Igbo text appears (not English)
- [ ] Backend logs show: "✅ SUCCESS: NaijaVox-2.0" or "Google Cloud"
- [ ] No "mock" in backend output

### TTS (Text-to-Speech) Testing
- [ ] Select "Igbo" from Audio settings
- [ ] Click "Test TTS" button
- [ ] Audio plays in Igbo language
- [ ] Status shows success
- [ ] No error messages about permissions

### Translation Testing
- [ ] Record Igbo conversation
- [ ] Click "🌐 Translate to English"
- [ ] See both Igbo original + English translation
- [ ] Toggle to show/hide translation

### Error Handling
- [ ] If STT fails: See clear error message (not fake transcript)
- [ ] If TTS fails: See specific permission or configuration error
- [ ] Error messages guide you to solution

---

## 🔍 How to Verify Changes

### Check Backend is Using Real STT (Not Mock)
```bash
# Start backend with debug logging
cd backend
python run.py

# Look for these patterns in console:
✅ "1️⃣ Trying: Google Cloud Speech-to-Text..."
✅ "2️⃣ Trying: NaijaVox-2.0"
✅ "3️⃣ Trying: OpenAI Whisper API..."

❌ SHOULD NOT SEE: "Using mock transcript"
```

### Check Frontend Displays Original Language
```javascript
// Open browser DevTools (F12)
// Go to Console tab
// Record audio
// Look for logs:
✅ "originalText": "Kedu?"  (NOT translated)
✅ "language": "igbo"
✅ "translatedText": null  (before user clicks translate)
```

### Verify API Key Permissions
```bash
# In backend logs, you should see:
✅ "✓ ElevenLabs TTS: igbo, ..."
✅ No "missing_permissions" error
```

---

## ⚠️ Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| Still seeing English text instead of Igbo | Browser cache issue: Ctrl+Shift+Delete, refresh |
| "Test TTS" button not working | Restart backend after updating .env |
| Hearing English in TTS instead of Igbo | Ensure language dropdown shows "Igbo" before clicking |
| "ALL STT SERVICES FAILED" | Run: `pip install transformers torch librosa` |
| "missing_permissions" error | Generate new API key with all permissions enabled |
| No audio at all | Check microphone permissions in OS |

---

## 📞 Quick Reference

### File Locations
- **Backend:** `c:\Users\Ogochukwu\Desktop\PROJECTS\PYTHON\brainr\backend`
- **.env:** `c:\Users\Ogochukwu\Desktop\PROJECTS\PYTHON\brainr\backend\.env`
- **Frontend:** `c:\Users\Ogochukwu\Desktop\PROJECTS\PYTHON\brainr\frontend`

### Commands
```bash
# Start backend
cd backend && python run.py

# Check Python syntax
python -m py_compile app/api/multiperson_chat.py

# Install NaijaVox dependencies
pip install transformers torch librosa torchaudio

# Restart frontend (if needed)
cd frontend && npm run dev
```

### API Endpoints (For Testing)
```
POST /api/multiperson/multiperson-diarize
  - Input: audio + language
  - Output: conversations with originalText in source language

POST /api/multiperson/translate-conversation
  - Input: conversations + sourceLanguage
  - Output: conversations with translations added

POST /api/chat/synthesize-speech
  - Input: text + language
  - Output: audio file in TTS format
```

---

## 📊 Expected Results After All Fixes

### STT Behavior
| Input | Before | After |
|-------|--------|-------|
| Speak Igbo | Translated to English | Shows Igbo text |
| Speak English | Shows English | Shows English |
| Service fails | Fake transcript | Error message |

### TTS Behavior  
| Action | Before | After |
|--------|--------|-------|
| Select Igbo + Test TTS | Mostly broken (API key missing) | Plays Igbo greeting |
| Select English + Test TTS | Works | Works |
| Select Yoruba + Test TTS | Mostly broken | Plays Yoruba greeting |

### User Experience
| Task | Before | After |
|------|--------|-------|
| Record in Igbo | See English translation | See Igbo text immediately |
| Get English translation | Automatic (forced) | Optional (user choice) |
| Understand errors | Silent failures | Clear guidance |

---

## 🎯 Success Criteria

You'll know everything is working when:

1. ✅ **STT Records Igbo:** Backend shows "SUCCESS: NaijaVox" (not "mock")
2. ✅ **Frontend Displays Igbo:** See "Kedu?" not "Hello?"
3. ✅ **Translation is Optional:** "🌐 Translate" button appears after recording
4. ✅ **TTS Plays Greeting:** Click "Test TTS" → Hear Igbo greeting
5. ✅ **Error Messages are Clear:** No more misleading fake transcripts
6. ✅ **No "mock" in logs:** Backend uses real STT services only

---

## 📞 Support Information

**Key Documentation Files:**
- `TRANSLATION_FIX_SUMMARY.md` - Technical overview
- `CODE_CHANGES_DETAILED.md` - Exact code changes
- `STT_TTS_QUICK_FIX.md` - User guide
- `.env` - Configuration file

**If You Get Stuck:**
1. Check backend logs: Look for error messages
2. Verify .env file: Ensure ELEVENLABS_API_KEY is set
3. Restart backend: Kill and restart `python run.py`
4. Clear browser: Ctrl+Shift+Delete → Clear cache
5. Refresh app: Ctrl+F5 (hard refresh)

---

## 🎉 Summary

**What You Need to Do:**
1. Create new ElevenLabs API key with permissions ⏱️ **~5 min**
2. Update .env file ⏱️ **~1 min**
3. Restart backend ⏱️ **~30 sec**
4. Test STT + TTS ⏱️ **~2 min**

**Total Time:** ~10 minutes

**Expected Outcome:** Full multilingual STT/TTS working with language preservation! 🎤🔊
