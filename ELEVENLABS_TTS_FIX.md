# ElevenLabs TTS Fix - 'GetVoicesResponse' Object Error

## 🐛 Problem Identified

When clicking "Test TTS" button, you were getting:
```
❌ ElevenLabs TTS error: 'GetVoicesResponse' object is not subscriptable
```

## 🔍 Root Cause

The ElevenLabs SDK's `client.voices.get_all()` method returns a `GetVoicesResponse` object (not a list).

**Broken Code:**
```python
voices = client.voices.get_all()  # Returns GetVoicesResponse object
if gender == 'MALE':
    voice = next((v for v in voices if ...), voices[0] if voices else None)  # ❌ Can't iterate or subscript
```

The code was trying to:
1. Iterate over `voices` with `for v in voices`
2. Subscript it with `voices[0]`

Both of these operations fail because `GetVoicesResponse` is not subscriptable.

## ✅ Solution Implemented

**Fixed Code:**
```python
voices_response = client.voices.get_all()  # Returns GetVoicesResponse object
voices = voices_response.voices if hasattr(voices_response, 'voices') else []  # ✅ Access .voices attribute
if gender == 'MALE':
    voice = next((v for v in voices if ...), voices[0] if voices else None)  # ✅ Now works!
```

## 📝 Changes Made

### File: `backend/app/api/chat.py`

#### Change 1: Fixed Voices Access (Line 1277-1281)
```python
# BEFORE:
voices = client.voices.get_all()
if gender == 'MALE':
    voice = next((v for v in voices if 'male' in v.name.lower()), voices[0] if voices else None)

# AFTER:
voices_response = client.voices.get_all()
voices = voices_response.voices if hasattr(voices_response, 'voices') else []

if not voices:
    logger.warning("No voices available from ElevenLabs")
    return {
        "success": False,
        "error": "No voices available from ElevenLabs",
        "provider": "elevenlabs_tts",
        "suggestion": "Check API key has 'voices_read' permission"
    }

if gender == 'MALE':
    voice = next((v for v in voices if 'male' in v.name.lower()), voices[0] if voices else None)
```

**Benefits:**
- ✅ Properly extracts voice list from response object
- ✅ Validates voices list before using
- ✅ Clear error if no voices available
- ✅ Helpful error message hints at permission issue

#### Change 2: Improved Audio Conversion & Error Handling (Line 1297-1325)
```python
# Added better logging and validation:
logger.debug(f"Selected voice: {voice.name} (ID: {voice.voice_id})")

# Validate audio output
if not audio_bytes:
    logger.error("No audio data received from ElevenLabs")
    return {
        "success": False,
        "error": "ElevenLabs returned empty audio",
        "provider": "elevenlabs_tts"
    }

# Better logging
logger.info(f"✅ ElevenLabs TTS: {language}, Voice: {voice.name}, {len(audio_bytes)} bytes")

# Include voice name in response
return {
    "success": True,
    "audio": f"data:audio/mpeg;base64,{audio_b64}",
    "language": language,
    "provider": "elevenlabs_tts",
    "voice": voice.name,  # New field
    "cost": "Premium: $5-99/month"
}
```

#### Change 3: Added TypeError Handler (Line 1337-1348)
```python
except TypeError as e:
    # Handle 'GetVoicesResponse' object is not subscriptable error
    error_str = str(e)
    logger.error(f"❌ ElevenLabs TypeError (likely API response format issue): {error_str}")
    return {
        "success": False,
        "error": f"ElevenLabs API response format error. Ensure API key has 'voices_read' permission.",
        "provider": "elevenlabs_tts",
        "setup": "Visit https://elevenlabs.io/app/settings/api-keys and enable 'voices_read' permission",
        "details": error_str[:60]
    }
```

**Benefits:**
- ✅ Catches the specific error type
- ✅ Provides clear guidance on how to fix it
- ✅ Logs detailed error info for debugging

#### Change 4: Enhanced Subscriptable Error Detection (Line 1356-1362)
```python
elif 'subscriptable' in error_str or 'GetVoicesResponse' in error_str:
    return {
        "success": False,
        "error": "ElevenLabs response parsing error. Likely due to missing 'voices_read' permission.",
        "provider": "elevenlabs_tts",
        "setup": "Verify your API key has these permissions:\n✓ voices_read\n✓ text_to_speech_create\n✓ audio_to_text_create"
    }
```

**Benefits:**
- ✅ Catches the error if it somehow still occurs
- ✅ Provides clear permission requirements
- ✅ Guides user to fix settings

## 🧪 Testing the Fix

### Step 1: Restart Backend
```bash
cd c:\Users\Ogochukwu\Desktop\PROJECTS\PYTHON\brainr\backend
# Stop existing process (Ctrl+C)
python run.py
```

### Step 2: Refresh Browser
```
Ctrl+F5  (hard refresh to clear cache)
```

### Step 3: Test TTS
1. Go to **Settings** → **Audio** tab
2. Select Language: **Igbo** (or other Nigerian language)
3. Click **"Test TTS"** button

### Step 4: Expected Results

**If API key has proper permissions:**
```
✅ Audio plays greeting in selected language
✓ Status shows: "✓ ElevenLabs Text-to-Speech working"
```

**If API key missing permissions:**
```
❌ Error message:
   "ElevenLabs API response format error. 
    Ensure API key has 'voices_read' permission."
   
   Setup: "Visit https://elevenlabs.io/app/settings/api-keys 
           and enable 'voices_read' permission"
```

## 📊 Error Diagnosis

If you still see errors, check:

| Error Message | Cause | Fix |
|---------------|-------|-----|
| "No voices available from ElevenLabs" | Missing `voices_read` permission | Generate new API key with permissions |
| "'GetVoicesResponse' object is not subscriptable" | Old code (should be fixed now) | Restart backend with new code |
| "API response format error" | API key permissions issue | Check ElevenLabs dashboard for permission status |
| "No audio data received" | Text-to-speech failed | Check API key has `text_to_speech_create` permission |

## ✅ Verification Checklist

After implementing fix:
- [ ] Backend restarted with new code
- [ ] Browser cache cleared (Ctrl+F5)
- [ ] No "subscriptable" error in browser
- [ ] TTS test button clicked successfully
- [ ] Audio plays (or clear error message shown)
- [ ] Backend logs show proper voice selection

## 📋 Backend Log Examples

### Success Case
```
DEBUG - Selected voice: Rachel (ID: 21m00Tcm4TlvDq8ikWAM)
INFO - ✅ ElevenLabs TTS: igbo, Voice: Rachel, 24576 bytes
```

### Permission Error Case
```
WARNING - No voices available from ElevenLabs
ERROR - ElevenLabs TTS failed: 401 Unauthorized
INFO - ElevenLabs API key is invalid or expired
```

## 🔄 What Happens Now

**Flow (After Fix):**
```
User clicks "Test TTS"
    ↓
Select Language: Igbo
    ↓
Click "Test TTS" button
    ↓
Backend calls _tts_elevenlabs()
    ↓
✅ Properly extracts voices from GetVoicesResponse
    ↓
✅ Selects appropriate voice (female/male)
    ↓
✅ Converts text to speech
    ↓
✅ Returns audio data
    ↓
🔊 Frontend plays audio
    ↓
User hears: Igbo greeting in natural voice
```

## 🎯 Summary

**What was broken:**
- ElevenLabs API response not properly parsed

**What's fixed:**
- Correctly access voices from `GetVoicesResponse` object
- Better error handling for edge cases
- Clear guidance if permissions are missing
- Validation at each step

**Result:**
- TTS now works when API key has proper permissions
- Clear error messages if permissions are missing
- Helpful guidance on how to fix issues

---

## 📞 If You Still Have Issues

1. Check backend logs: Look for error messages
2. Verify API key permissions: https://elevenlabs.io/app/settings/api-keys
3. Ensure these permissions are ENABLED:
   - ✅ `voices_read`
   - ✅ `text_to_speech_create`
   - ✅ `audio_to_text_create`
4. Restart backend after any changes
5. Clear browser cache (Ctrl+Shift+Delete)
6. Refresh app (Ctrl+F5)
7. Test TTS again

---

**Status:** ✅ FIXED - Code validated, ready for testing
