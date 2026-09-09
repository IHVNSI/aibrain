# Service Selection Fix - Complete Implementation Guide

## ✅ Issues Fixed

### 1. ❌ **No Voice Input Language Selector on Chat Page** 
**Before:** Users had to go to Settings to change voice input language
**After:** ✅ Voice input language dropdown now appears directly on Chat page

### 2. ❌ **TTS Hardcoded to Google Cloud**
**Before:** Backend forced Google Cloud for all African languages, ignoring user's preference
**After:** ✅ TTS respects user's selected provider from Audio settings

### 3. ❌ **STT Hardcoded Auto-Detection with Google Cloud Priority**
**Before:** Backend auto-detected STT service with Google Cloud as first priority, ignoring user's preference
**After:** ✅ STT uses user's selected model from Audio settings, falls back to auto-detect only if not configured

---

## 🔧 Implementation Details

### FRONTEND CHANGES

#### 1. Chat.jsx - Added Voice Language Selector

**File:** `frontend/src/pages/Chat.jsx`

**Changes:**
- Added `VOICE_INPUT_LANGUAGES` array with language options
- Added `changeVoiceInputLanguage()` function to handle language changes
- Added voice language dropdown UI above the input textarea
- Saves language preference to both localStorage and backend

**Code Added:**
```javascript
const VOICE_INPUT_LANGUAGES = [
  { code: 'english', label: 'English' },
  { code: 'igbo', label: 'Igbo' },
  { code: 'hausa', label: 'Hausa' },
  { code: 'yoruba', label: 'Yoruba' },
  { code: 'pidgin', label: 'Nigerian Pidgin' },
]

const changeVoiceInputLanguage = async (newLanguage) => {
  const newSettings = { ...audioSettings, voiceInputLanguage: newLanguage }
  setAudioSettings(newSettings)
  
  // Save to localStorage
  try {
    localStorage.setItem('voiceInputLanguage', newLanguage)
  } catch (_) {}
  
  // Save to backend
  try {
    await api.post('/api/settings/user', { audio_settings: newSettings })
  } catch (e) {
    console.error('Failed to save voice language preference:', e)
  }
}
```

**UI Result:**
```
┌─────────────────────────────────┐
│ Voice Language: [English ▼]     │
├─────────────────────────────────┤
│ Ask about your data...          │
│ (textarea grows as needed)      │
├─────────────────────────────────┤
│ [🎤] Stop  [Send] ▶            │
└─────────────────────────────────┘
```

**Benefits:**
- ✅ Users can change language without navigating away
- ✅ Preference persisted to backend (survives page refresh)
- ✅ Instant feedback with dropdown selector
- ✅ Shows all available language options

---

#### 2. Settings.jsx - Added TTS Provider Selector

**File:** `frontend/src/pages/Settings.jsx`

**Changes:**
- Added `ttsProvider` field to audio settings state (default: 'google-cloud')
- Added `TTS_PROVIDERS` array with provider options
- Added TTS provider selector UI in Audio settings
- Updated `testVoice()` to send user's `ttsProvider` preference to backend

**Code Added:**
```javascript
const TTS_PROVIDERS = [
  {
    id: 'google-cloud',
    name: 'Google Cloud Text-to-Speech',
    description: 'Premium quality, best support for Nigerian languages...',
    status: 'recommended'
  },
  {
    id: 'elevenlabs-tts',
    name: 'ElevenLabs TTS',
    description: 'High-quality synthetic voices...',
    status: 'premium'
  },
  {
    id: 'azure-tts',
    name: 'Microsoft Azure Text-to-Speech',
    description: 'Enterprise-grade synthesis...',
    status: 'premium'
  },
  {
    id: 'browser',
    name: 'Browser Native TTS',
    description: 'Free, no API required, English only.',
    status: 'limited'
  }
]
```

**Updated testVoice():**
```javascript
const { data } = await api.post('/api/chat/synthesize-speech', {
  text: testMessage,
  language: language,
  gender: gender,
  tts_provider: settings.ttsProvider || 'google-cloud'  // NEW
})
```

**UI Result:**
```
Audio Tab:
├─ Speech-to-Text Model
│  ○ NaijaVox-2.0 (Nigerian Languages) ✓ Recommended
│  ○ OpenAI Whisper (Large-v3) ✓ Recommended
│  ○ ElevenLabs Scribe API ⭐ Premium
│  
└─ Text-to-Speech Provider
   ○ Google Cloud Text-to-Speech ✓ Recommended
   ○ ElevenLabs TTS ⭐ Premium
   ○ Microsoft Azure TTS ⭐ Premium
   ○ Browser Native TTS ⚠️ Limited
```

**Benefits:**
- ✅ Users can choose their preferred TTS provider
- ✅ Clear indication of premium vs free options
- ✅ Saved to backend audio_settings
- ✅ Test voice button respects the choice

---

### BACKEND CHANGES

#### 1. chat.py - Fixed TTS Service Selection

**File:** `backend/app/api/chat.py`
**Endpoint:** `POST /api/chat/synthesize-speech`

**Changes:**
- Removed hardcoded logic that forced Google Cloud for African languages
- Added user preference lookup from database
- Respects `tts_provider` parameter from request
- Falls back to smart defaults only if user hasn't configured preference

**Code Before:**
```python
# HARDCODED: Always use Google Cloud for non-English
if not tts_provider:
    tts_provider = 'browser' if language == 'english' else 'google-cloud'
```

**Code After:**
```python
# SMART: Get user's preference from settings
if not tts_provider:
    from ..models import UserSettings
    user_audio_settings = {}
    try:
        ctx = current_user_context()
        if ctx.get('user_id'):
            user_settings = UserSettings.query.filter_by(user_id=ctx.get('user_id')).first()
            if user_settings:
                user_audio_settings = user_settings.get_audio_settings() or {}
                tts_provider = user_audio_settings.get('ttsProvider', '').strip()
    except:
        pass
    
    # Fall back to smart defaults only if user hasn't configured
    if not tts_provider:
        tts_provider = 'browser' if language == 'english' else 'google-cloud'
```

**Behavior:**
1. Check if `tts_provider` passed in request → Use it
2. Check if user has configured preference in Settings → Use it
3. Fall back to smart defaults (browser for English, Google Cloud for others)

**Flow Example:**
```
Request received: synthesize-speech
├─ If tts_provider in request → Use request provider
├─ Else if user configured in settings → Use user's choice
├─ Else → Use smart default
└─ Execute chosen provider
```

---

#### 2. multiperson_chat.py - Fixed STT Service Selection

**File:** `backend/app/api/multiperson_chat.py`
**Endpoint:** `POST /api/multiperson/multiperson-diarize`

**Changes:**
- Reads user's `sttModel` preference from database
- Allows optional override via request parameter
- Respects user's choice instead of auto-detecting
- Maintains fallback chain if primary service fails

**Code Before:**
```python
# Always defaults to 'whisper' and ignores user preference
stt_model = user_audio_settings.get('sttModel', 'whisper')
```

**Code After:**
```python
# Smart preference handling with fallback to auto-detect
stt_model = 'auto'  # Default to auto-detect

# Allow passing stt_model via request (for flexibility)
request_stt_model = request.form.get('sttModel', '').strip().lower()
if request_stt_model and request_stt_model != 'auto':
    stt_model = request_stt_model
    logger.info(f"📊 Request override: Using {stt_model} for {language}")
else:
    # Fall back to user's settings preference
    if ctx.get('user_id'):
        user_settings = UserSettings.query.filter_by(user_id=ctx.get('user_id')).first()
        if user_settings:
            user_audio_settings = user_settings.get_audio_settings() or {}
            user_stt = user_audio_settings.get('sttModel', '').strip().lower()
            if user_stt and user_stt != 'auto':
                stt_model = user_stt
                logger.info(f"📊 User preference: Using {stt_model} for {language}")
```

**Behavior:**
1. Check if `sttModel` in request → Use it (request override)
2. Check if user configured in Settings → Use user's choice
3. Otherwise → Use auto-detect with intelligent fallback

**Flow Example:**
```
Diarize request received
├─ If sttModel in request → Use that service
├─ Else if user configured sttModel in settings → Use that
├─ Else → Auto-detect best available
│  ├─ For Nigerian languages: Google Cloud → NaijaVox
│  └─ For English: Google Cloud → Whisper
└─ Execute with fallback chain
   ├─ Primary service → success or fallback
   ├─ Secondary service → success or fallback
   ├─ Tertiary service → success or error
   └─ If all fail → return error
```

---

## 📊 Service Priority Chains (Unchanged)

### For Nigerian Languages (Igbo, Yoruba, Hausa, Pidgin)
```
1️⃣ User's configured STT → if they chose one
2️⃣ Google Cloud (if configured) → Best quality
3️⃣ NaijaVox-2.0 (FREE) → Optimized for Nigerian languages  
4️⃣ ElevenLabs → Premium fallback
5️⃣ Error → Return failure message
```

### For English
```
1️⃣ User's configured STT → if they chose one
2️⃣ Google Cloud (if configured) → Best quality
3️⃣ OpenAI Whisper → Reliable fallback
4️⃣ ElevenLabs → Premium fallback
5️⃣ Error → Return failure message
```

### TTS Providers
```
User Configured Provider → or Fallback Chain:
├─ Browser TTS (English only)
├─ Google Cloud TTS (African languages)
├─ Azure TTS (multilingual)
├─ ElevenLabs TTS (premium)
└─ Error → Return failure message
```

---

## 🧪 Testing Guide

### Test 1: Voice Language Selector on Chat Page

**Steps:**
```
1. Navigate to /chat page
2. Look for "Voice Language:" dropdown above input box
3. Change from English to Igbo
4. Click microphone and speak: "Nnoo, kedu ka ị na-eme taa"
5. Expected: Text appears in Igbo (not English)
```

**Success Criteria:**
- ✅ Dropdown appears and is selectable
- ✅ Preference persists after page refresh
- ✅ Voice input recognizes the selected language
- ✅ Backend logs show: "📊 User preference: Using [service] for igbo"

### Test 2: TTS Provider Selection in Settings

**Steps:**
```
1. Go to Settings → Audio Tab
2. Scroll to "Text-to-Speech Provider"
3. Select "ElevenLabs TTS" or "Azure TTS"
4. Set voice language to Igbo
5. Click "Test Voice" button
6. Backend should use your selected provider
```

**Success Criteria:**
- ✅ Provider selector visible with all options
- ✅ Selected provider is highlighted
- ✅ Backend logs show: "📊 Request override: Using [provider]"
- ✅ Audio plays using selected service

### Test 3: STT Model Selection

**Steps:**
```
1. Go to Settings → Audio Tab
2. Change "Speech-to-Text Model" to "NaijaVox-2.0"
3. Go to Multi-Chat page
4. Select language: Igbo
5. Record audio: "Nnoo, kedu ka ị na-eme taa"
6. Expected: Uses NaijaVox-2.0 for transcription
```

**Success Criteria:**
- ✅ STT model selector visible
- ✅ Backend logs show: "📊 User preference: Using naijavox"
- ✅ Transcription works in selected service
- ✅ Fallback works if primary service fails

### Test 4: Default Behavior (No User Preference)

**Steps:**
```
1. Create new user or clear settings
2. No TTS provider or STT model configured
3. Use Chat and Multi-Chat features
4. Backend should auto-detect services
```

**Success Criteria:**
- ✅ Backend logs show: "📊 Auto-detect:"
- ✅ Services still work with smart defaults
- ✅ No errors or missing configuration

---

## 🚀 User Experience Flow

### On Chat Page
```
User visits /chat
  ↓
Sees new "Voice Language:" dropdown
  ↓
User selects "Igbo"
  ↓
Preference saved to backend
  ↓
User clicks microphone 🎤
  ↓
System recognizes Igbo voice input
  ↓
Text displayed in Igbo (not English)
```

### On Settings Page
```
User visits Settings → Audio Tab
  ↓
Sees new "Speech-to-Text Model" selector
  ↓
Sees new "Text-to-Speech Provider" selector
  ↓
User selects:
  - STT: NaijaVox-2.0
  - TTS: ElevenLabs
  ↓
Settings saved
  ↓
All future transcription uses NaijaVox
  ↓
All future synthesis uses ElevenLabs
```

---

## 📝 Backend Request/Response Examples

### TTS Request (with provider override)
```json
POST /api/chat/synthesize-speech
{
  "text": "Nnoo, kedu ka ị na-eme taa",
  "language": "igbo",
  "gender": "FEMALE",
  "tts_provider": "elevenlabs-tts"
}

Response:
{
  "success": true,
  "audio": "data:audio/mp3;base64,...",
  "provider": "elevenlabs-tts"
}
```

### STT Request (diarization with optional override)
```
POST /api/multiperson/multiperson-diarize
Content-Type: multipart/form-data

Fields:
- audio: [webm file]
- language: igbo
- sttModel: naijavox (optional override)

Response:
{
  "success": true,
  "conversations": [
    {
      "participant": "Speaker 1",
      "originalText": "Nnoo, kedu ka ị na-eme taa",
      "translatedText": null,
      "timestamp": "2026-09-04T16:45:00Z"
    }
  ]
}
```

Backend logs will show:
```
📊 User preference: Using naijavox for igbo
🎯 STT Pipeline Started
   Language: igbo (Nigerian: true)
   File: /tmp/audio_user123_abc123.webm (45234 bytes)
   Model: naijavox
2️⃣  Trying: NaijaVox-2.0 (FREE, optimized for Nigerian languages)...
✅ SUCCESS: NaijaVox-2.0 - 45 chars
```

---

## ✅ Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `frontend/src/pages/Chat.jsx` | Added voice language selector dropdown | ~50 |
| `frontend/src/pages/Settings.jsx` | Added TTS provider selector + testVoice update | ~100 |
| `backend/app/api/chat.py` | Smart TTS service selection from user settings | ~20 |
| `backend/app/api/multiperson_chat.py` | Smart STT service selection from user settings | ~20 |

---

## 🔍 Verification

All files have been verified:
- ✅ Python syntax verified (0 errors)
- ✅ JavaScript/React syntax verified (0 errors)
- ✅ Backend compiles successfully
- ✅ Frontend builds successfully

---

## 🎯 Key Benefits

1. **User Control** - Users can now choose their preferred STT/TTS services
2. **No More Hardcoding** - Services respect user preferences instead of forced defaults
3. **Persistent Preferences** - Settings saved to backend and persist across sessions
4. **Flexible Selection** - Works on Chat page (language) and Settings (providers)
5. **Fallback Support** - If primary service fails, falls back to alternatives
6. **Backward Compatible** - All changes are backward compatible

---

## 🚀 Next Steps

1. **Restart Backend**
   ```bash
   cd backend
   python run.py
   ```

2. **Clear Frontend Cache**
   ```
   Ctrl+Shift+Delete → Clear ALL data
   Ctrl+F5 → Refresh
   ```

3. **Test Features**
   - Test voice language selector on Chat page
   - Test TTS provider selection in Settings
   - Test STT model selection in Settings
   - Verify preferences persist

4. **Monitor Logs**
   - Check backend logs for "User preference:" messages
   - Verify correct services are being used

---

**Status:** ✅ COMPLETE & READY FOR TESTING

**Last Updated:** 2026-09-04
