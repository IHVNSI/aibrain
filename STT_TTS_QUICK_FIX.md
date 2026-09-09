# STT/TTS Fix Guide - Real-Time Language Display

## ✅ What Was Just Fixed

### 1. **Removed Unnecessary Translation**
- ❌ **Before:** Every language was translated to English during recording (slow, inaccurate)
- ✅ **After:** Original language text shown in real-time (fast, accurate)
- **Impact:** Users speaking Igbo/Yoruba/Hausa now see text in their language immediately

### 2. **Removed Mock Transcripts**
- ❌ **Before:** When STT services failed, app silently showed fake data
- ✅ **After:** Clear error messages guide users to fix configuration
- **Impact:** No more misleading transcripts; users know when something is broken

### 3. **Added Optional Translation**
- ❌ **Before:** Forced translation to English, no user control
- ✅ **After:** Optional "🌐 Translate to English" button after recording
- **Impact:** Users can choose if they want English translation

---

## 🎯 Next: Fix TTS (Text-to-Speech) Testing

Your current issue: **ElevenLabs API key is missing permissions**

### Step 1: Generate New API Key with Full Permissions

1. Go to: https://elevenlabs.io/app/settings/api-keys
2. Click **"Generate API key"** or **"+ Create new key"**
3. Name it: `brainr-multilingual`
4. **Enable ALL these permissions:**
   - ✅ `voices_read` (to READ voice list)
   - ✅ `text_to_speech_create` (to CREATE audio)
   - ✅ `audio_to_text_create` (for STT)
5. **Copy** the new key (shown only once!)

### Step 2: Update .env File

```bash
# OLD (missing permissions):
ELEVENLABS_API_KEY=sk_fb23324f9de6b96e8e6ef5c3d0f5aad8e34e563a3c6577da

# NEW (full permissions):
ELEVENLABS_API_KEY=sk_xxxxxxxxxxxxxxxxxxxx_new_key_xxxxxxxxxxxxxxxxxxxx
```

### Step 3: Restart Backend

```bash
cd backend
# Stop running server (Ctrl+C)
# Restart:
python run.py
```

### Step 4: Test TTS with Greetings

1. **Refresh browser** (Ctrl+F5 or Cmd+Shift+R)
2. Go to **Audio** tab → **Audio Settings**
3. Select a language from dropdown:
   - English
   - Igbo
   - Hausa
   - Yoruba
   - Nigerian Pidgin

4. Click **"Test TTS"** button
5. **Expected:** Hear greeting in selected language

---

## 📋 Language-Specific Greetings (Will Be Tested)

| Language | Greeting | Meaning |
|----------|----------|---------|
| **English** | "This is a test of your audio settings. Your voice responses will sound like this." | Standard test phrase |
| **Igbo** | "Ovo bu ihe nnwale nke ọ na-agụ gị. Okwu gị na-ege n'ezi ga-adị ka ihe a." | "This is a test of your audio settings..." |
| **Yoruba** | "Eyi ni idanwo ti ohun ti o wa ninu ero. Ohun yi yoo soro bi eyi." | "This is a test of your audio system..." |
| **Hausa** | "Wannan shine gwajin saitunan na-duwatse mika. Murmurinka za a ji yadha wannan." | "This is a test of audio settings..." |
| **Pidgin** | "Dis na test of your audio settings. Your voice response go sound like dis one." | "This is a test..." (Pidgin style) |

---

## 🔄 How STT/TTS Now Works

### **STT (Speech-to-Text) Flow**
```
User speaks in Igbo
    ↓
NaijaVox-2.0 (FREE, optimized) → Google Cloud → ElevenLabs → Error
    ↓
Display ORIGINAL IGBO TEXT in real-time
    ↓
After recording: Optional "Translate to English" button
    ↓
Translation happens as POST-PROCESSING (not during recording)
```

### **TTS (Text-to-Speech) Flow**
```
User clicks "Test TTS"
    ↓
Select language: Igbo
    ↓
ElevenLabs converts text to speech in Igbo
    ↓
Audio plays: Greeting in Igbo language
```

---

## ✅ Verification Checklist

### Before Restarting Backend
- [ ] New ElevenLabs API key generated with full permissions
- [ ] .env file updated with new key
- [ ] Old key removed (or replaced)

### After Restarting Backend
- [ ] Backend running without errors: `python run.py`
- [ ] No "AuthenticationException" errors in backend logs
- [ ] No "missing_permissions" errors

### Testing STT
- [ ] Select "Igbo" language
- [ ] Click "Record"
- [ ] Speak: "Kedu?"
- [ ] Click "Stop"
- [ ] See Igbo text displayed (not translated)
- [ ] Backend shows: "✅ SUCCESS: NaijaVox-2.0"

### Testing TTS
- [ ] Go to Audio tab
- [ ] Select "Igbo"
- [ ] Click "Test TTS"
- [ ] Hear greeting in Igbo language
- [ ] Status shows: "✓ ElevenLabs Text-to-Speech working"

---

## 🆘 Troubleshooting

### Error: "ElevenLabs API key missing 'voices_read' permission"
**Solution:** Generate new API key with ALL permissions enabled

### Error: "No voices available from ElevenLabs"
**Solution:** Ensure API key has `voices_read` permission

### Error: "File does not start with RIFF id"
**Solution:** Already fixed - backend now supports WebM/MP3 formats

### Error: "ALL STT SERVICES FAILED"
**Solution:** Install NaijaVox dependencies:
```bash
pip install transformers torch librosa torchaudio
```

### Audio plays but in English instead of target language
**Solution:** Check that language was properly selected in Audio settings dropdown

---

## 📞 Key Files Modified

1. **Backend:**
   - `app/api/multiperson_chat.py` - Removed auto-translation, added `/translate-conversation` endpoint

2. **Frontend:**
   - `src/pages/MultiPersonChat.jsx` - Updated conversation display, added language-aware UI

3. **Documentation:**
   - `TRANSLATION_FIX_SUMMARY.md` - Full technical details of changes

---

## 🎬 Quick Start (Summary)

1. Get new ElevenLabs API key with permissions
2. Update `.env` with new key
3. Restart backend
4. Refresh browser
5. Test STT: Record in Igbo → See Igbo text
6. Test TTS: Click Test → Hear greeting in Igbo

**That's it!** 🎉

---

## 📖 Documentation Reference

For technical details, see: [TRANSLATION_FIX_SUMMARY.md](TRANSLATION_FIX_SUMMARY.md)

For ElevenLabs setup: https://elevenlabs.io/docs/api-reference
For NaijaVox: https://huggingface.co/Axiveri/NaijaVox-2.0
