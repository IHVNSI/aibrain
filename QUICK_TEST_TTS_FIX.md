# Quick Test Guide - ElevenLabs TTS Fix

## ✅ What Was Fixed

The error `'GetVoicesResponse' object is not subscriptable` has been fixed by properly accessing the voices list from the ElevenLabs API response.

## 🚀 How to Test

### Step 1: Restart Backend (Critical!)
```bash
# Stop current backend process
cd c:\Users\Ogochukwu\Desktop\PROJECTS\PYTHON\brainr\backend
# Press Ctrl+C if running
python run.py
```

Expected output:
```
 * Running on http://127.0.0.1:5001
 * Press CTRL+C to quit
```

### Step 2: Clear Browser Cache
```
Ctrl+Shift+Delete  (Windows)
or
Cmd+Shift+Delete   (Mac)

Select: Clear all data, Clear cookies and cached images
Click: Clear browsing data
```

### Step 3: Hard Refresh App
```
Ctrl+F5  (Windows)
or
Cmd+Shift+R  (Mac)
```

### Step 4: Navigate to Audio Settings
```
Settings → Audio → Audio Configuration Tab
```

### Step 5: Test TTS

**Test 1: Igbo**
```
1. Language dropdown: Select "Igbo"
2. Click "Test TTS" button
3. Expected: Hear greeting in Igbo language
4. Status should show: "✓ ElevenLabs Text-to-Speech working"
```

**Test 2: Yoruba**
```
1. Language dropdown: Select "Yoruba"
2. Click "Test TTS" button
3. Expected: Hear greeting in Yoruba language
```

**Test 3: English**
```
1. Language dropdown: Select "English"
2. Click "Test TTS" button
3. Expected: Hear English greeting
```

## 📊 Expected Results

### ✅ Success (API Key has Proper Permissions)
```
Status Message: "✓ ElevenLabs Text-to-Speech working"
Audio: Plays naturally-sounding greeting in selected language
Backend Logs: "✅ ElevenLabs TTS: [language], Voice: [voice_name], [bytes] bytes"
```

### ❌ Permission Error (API Key Missing Permissions)
```
Status Message: 
"ElevenLabs API response format error. 
 Ensure API key has 'voices_read' permission.
 
 Setup: Visit https://elevenlabs.io/app/settings/api-keys 
        and enable 'voices_read' permission"
```

**Solution:**
1. Go to: https://elevenlabs.io/app/settings/api-keys
2. Click on your API key
3. Verify these permissions are ENABLED:
   - ✅ `voices_read`
   - ✅ `text_to_speech_create`
   - ✅ `audio_to_text_create`
4. If not enabled, generate a NEW key with all permissions
5. Update `.env` file
6. Restart backend

### ❌ Invalid Key Error
```
Status Message:
"ElevenLabs API key is invalid or expired
 
 Setup: Check ELEVENLABS_API_KEY in .env"
```

**Solution:**
1. Generate new API key at: https://elevenlabs.io/app/settings/api-keys
2. Ensure it has all required permissions
3. Update `.env` file
4. Restart backend

## 📝 What to Check in Backend Logs

### ✅ Success Logs
```
DEBUG - Selected voice: Rachel (ID: 21m00Tcm4TlvDq8ikWAM)
INFO - ✅ ElevenLabs TTS: igbo, Voice: Rachel, 24576 bytes
```

### ❌ Error Logs
```
WARNING - No voices available from ElevenLabs
ERROR - ElevenLabs TTS failed: 401 Unauthorized
```

## 🎯 Quick Checklist

- [ ] Backend restarted with `python run.py`
- [ ] Browser cache cleared (Ctrl+Shift+Delete)
- [ ] App hard refreshed (Ctrl+F5)
- [ ] Navigated to Settings → Audio
- [ ] Language selected in dropdown
- [ ] "Test TTS" button clicked
- [ ] Audio played (or error message shown)
- [ ] Backend logs checked for details

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| Still getting "subscriptable" error | Backend not restarted - restart with `python run.py` |
| No audio plays but no error | API key may not have `text_to_speech_create` permission |
| Error about "voices_read" | Generate new API key with proper permissions |
| Error about invalid key | Check `.env` file - ensure key is exactly as shown in ElevenLabs |

## 📋 Test Results Template

```
Date: [Today]
Time: [Time tested]
Backend Status: [Running/Error]

Test 1 - Igbo:
  Language: Igbo
  Result: [Success/Failed]
  Audio Played: [Yes/No]
  Status Message: [Copy from screen]
  
Test 2 - Yoruba:
  Language: Yoruba
  Result: [Success/Failed]
  Audio Played: [Yes/No]
  Status Message: [Copy from screen]

Test 3 - English:
  Language: English
  Result: [Success/Failed]
  Audio Played: [Yes/No]
  Status Message: [Copy from screen]

Backend Logs:
  [Copy relevant error messages if any]

Overall Status: [All tests passed / Some failed / All failed]
```

## 🎉 Expected Timeline

- **Step 1 (Restart):** ~30 seconds
- **Step 2 (Clear Cache):** ~30 seconds  
- **Step 3 (Refresh):** ~10 seconds
- **Step 4 (Navigate):** ~5 seconds
- **Step 5 (Test):** ~10 seconds per language

**Total Time:** ~2-3 minutes

## 📞 After Testing

- ✅ If TTS works: Great! The fix is complete
- ❌ If TTS fails: Check backend logs and follow error guidance
- ⚠️ If unclear: Verify API key permissions at https://elevenlabs.io/app/settings/api-keys

---

**Status:** Ready to test! Backend code is fixed and validated. ✅
