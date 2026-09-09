# 🇳🇬 Igbo Speech-to-Text Setup Guide

## Quick Status Check

The app now supports **real-time Igbo, Yoruba, and Hausa transcription** using:

1. **NaijaVox-2.0** (FREE, recommended) - Optimized for Nigerian languages
2. **Google Cloud Speech-to-Text** (if configured) - Best accuracy
3. **ElevenLabs** (if configured) - Premium option
4. **Web Speech API** (browser) - Live transcription as you speak

---

## How It Works

### Frontend (Real-Time Transcription)
When you select **Igbo** and click **"Start Recording"**:
1. Browser's Web Speech API listens in real-time
2. Interim text appears as you speak (grayed out)
3. Final text appears when speech ends (bold)
4. All text stays in **Igbo** (not translated)

### Backend (Full Transcription)
When you upload audio or stop recording:
1. Audio sent to backend with language code
2. Backend tries: Google Cloud → **NaijaVox** → ElevenLabs → Mock
3. **NaijaVox-2.0** transcribes Igbo → Igbo text ✅
4. Text sent back to frontend with speaker detection

---

## Setup Options

### OPTION 1: NaijaVox-2.0 (FREE, RECOMMENDED)

**Status:** ✅ Already installed and ready to use

**What you need to do:** Nothing! It's already configured.

**How it works:**
- Free offline model (~2.5GB)
- Auto-downloads on first use
- Supports: Igbo, Yoruba, Hausa, Nigerian Pidgin, Nigerian English
- Works with GPU or CPU
- **22.58% WER (Word Error Rate)** - very accurate

**First use:**
```bash
cd backend
python run.py
```

On first recording/upload in Igbo, the model (~2.5GB) will download automatically.

---

### OPTION 2: Google Cloud Speech-to-Text (BEST ACCURACY)

**Accuracy:** Better than NaijaVox
**Cost:** $0.024/minute (very affordable)
**Setup time:** 15-20 minutes

**Setup Steps:**

1. **Create Google Cloud Project:**
   - Go to https://console.cloud.google.com
   - Click "Create Project"
   - Name it "Brainr STT"

2. **Enable Speech-to-Text API:**
   - In Google Cloud Console, search for "Speech-to-Text API"
   - Click "Enable"

3. **Create Service Account:**
   - Go to IAM & Admin → Service Accounts
   - Click "Create Service Account"
   - Name: "brainr-stt"
   - Click "Create and Continue"
   - Grant role: "Cloud Speech-to-Text Admin"
   - Click "Create"

4. **Generate JSON Key:**
   - In Service Accounts list, click the service account you created
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Choose "JSON" → "Create"
   - A JSON file downloads automatically

5. **Configure Backend:**
   ```bash
   # Move the JSON file to backend folder
   cp /path/to/downloaded/key.json backend/google-cloud-key.json
   ```

6. **Update .env:**
   ```
   GOOGLE_CLOUD_STT_CREDENTIALS_PATH=backend/google-cloud-key.json
   ```

7. **Restart backend:**
   ```bash
   cd backend
   python run.py
   ```

**Supported Languages:**
- `ig-NG` - Igbo (Nigeria) ✅
- `yo-NG` - Yoruba (Nigeria) ✅
- `ha-NG` - Hausa (Nigeria) ✅

---

### OPTION 3: ElevenLabs (Already Configured)

**Status:** ✅ Already configured (API key in .env)

**Accuracy:** Good for African languages
**Cost:** ~$0.003/minute
**Setup:** 0 minutes (already done)

**Automatically used as fallback if:**
- NaijaVox fails
- No Google Cloud credentials

---

## Frontend Implementation

### How to Use Multi-Chat with Igbo:

1. **Open the app** and go to **Multi-Chat** tab

2. **Click "Auto-detect speakers"** checkbox

3. **Select language: "Igbo"**

4. **Click "Start Recording"**
   - You'll see: "🎤 Live Transcription [IGBO]"
   - Speak in Igbo naturally
   - Text appears in real-time
   - Interim text (gray, italic)
   - Final text (bold, black)

5. **Stop Recording**
   - Audio uploaded to backend
   - Backend transcribes with NaijaVox-2.0
   - Speakers automatically detected
   - Igbo text displayed with speaker names

6. **See Results**
   - Each speaker's statement in Igbo
   - Show Translation button to see English
   - Edit if needed
   - Send for AI analysis

---

## Testing

### Quick Test (No Setup Needed)

```bash
cd backend
python test_igbo_stt.py
```

This tests:
- ✅ NaijaVox-2.0 installation
- ✅ Google Cloud credentials (if configured)
- ✅ Language code mappings
- ✅ All available STT methods

### Manual Test in the App

1. Go to Multi-Chat
2. Select "Igbo" language
3. Click "Start Recording"
4. Say: "Kedu? Mma onwe gị?" (Hi, how are you?)
5. Stop Recording
6. Verify: Text appears in Igbo (not English)

### Test with Audio File

```bash
# Create a test Igbo audio file (wav, mp3, etc)
# Upload via "Upload Audio File" button
# Verify it transcribes to Igbo
```

---

## Troubleshooting

### Issue: "No speech detected"
**Solution:**
- Speak louder/clearer
- Ensure microphone is working
- Try uploading a longer audio file

### Issue: Text appears in English instead of Igbo
**Solution:**
1. Check that you selected "Igbo" in the dropdown
2. Restart backend: `python run.py`
3. Try again

### Issue: "NaijaVox failed" message
**Solution:**
- First time: Model is downloading (~2.5GB) - wait 5-10 minutes
- Check internet connection
- Check disk space (need ~3GB free)
- Run: `pip install torch torchaudio librosa`

### Issue: Slow transcription
**Solution:**
- First run is slow (model loading)
- Subsequent runs are faster
- GPU is faster than CPU:
  - Update `.env`: `NAIJAVOX_DEVICE=cuda`
  - Requires: NVIDIA GPU + CUDA installed

### Issue: Out of memory
**Solution:**
- Add to `.env`: `NAIJAVOX_TORCH_DTYPE=float16` (already set)
- Reduces memory usage
- Still maintains accuracy

---

## Backend STT Service Priority

### For Igbo/Yoruba/Hausa (Nigerian Languages):
```
Google Cloud (if configured) 
    ↓ [if fails]
NaijaVox-2.0 ← FREE, RECOMMENDED ✅
    ↓ [if fails]
ElevenLabs (if configured)
    ↓ [if fails]
Mock Transcript (testing)
```

### For English:
```
Google Cloud (if configured)
    ↓ [if fails]
OpenAI Whisper API (configured) ✅
    ↓ [if fails]
Mock Transcript
```

---

## Real-Time Transcription (Web Speech API)

### Why is it displayed immediately?
- **Client-side processing**: Browser's Web Speech API
- **No server needed**: Works offline
- **Language-aware**: Respects selected language (igbo, yoruba, hausa)

### Supported Browsers:
- ✅ Chrome/Chromium (best)
- ✅ Edge (best)
- ✅ Safari (good)
- ⚠️ Firefox (limited)

### Language Codes Used:
- Igbo: `ig-NG` (Nigerian Igbo)
- Yoruba: `yo-NG` (Nigerian Yoruba)
- Hausa: `ha-NG` (Nigerian Hausa)

These are **BCP 47** language tags recognized by Web Speech API.

---

## Performance Tips

1. **Use NaijaVox for best results:**
   - Optimized for Nigerian accents
   - Free and offline
   - No API calls needed

2. **GPU Acceleration:**
   ```
   # In .env
   NAIJAVOX_DEVICE=cuda  # Much faster (if NVIDIA GPU available)
   NAIJAVOX_DEVICE=cpu   # Slower but works everywhere
   ```

3. **Memory Optimization:**
   ```
   # In .env
   NAIJAVOX_TORCH_DTYPE=float16  # Faster, lower memory (set by default)
   ```

4. **First Run:**
   - Model download: 5-10 minutes (one time only)
   - First transcription: 10-30 seconds
   - Subsequent: 2-5 seconds

---

## File Structure

```
backend/
├── .env                          # Config (NaijaVox settings here)
├── app/
│   └── api/
│       └── multiperson_chat.py  # STT logic (updated with Igbo support)
└── requirements.txt              # Dependencies (google-cloud-speech, librosa added)

frontend/
└── src/
    └── pages/
        └── MultiPersonChat.jsx   # Language selector, real-time display
```

---

## Environment Variables

```bash
# NaijaVox-2.0 Configuration
NAIJAVOX_DEVICE=auto              # auto, cuda, or cpu
NAIJAVOX_TORCH_DTYPE=float16       # float16 or float32

# Google Cloud (optional)
GOOGLE_CLOUD_STT_CREDENTIALS_PATH=/path/to/key.json

# ElevenLabs (optional)
ELEVENLABS_API_KEY=sk_...          # Already set

# OpenAI (English fallback)
OPENAI_API_KEY=sk-...              # Already set
```

---

## Next Steps

1. **Test NaijaVox:**
   ```bash
   cd backend
   python test_igbo_stt.py
   ```

2. **Start the app:**
   ```bash
   # Terminal 1: Backend
   cd backend && python run.py
   
   # Terminal 2: Frontend
   cd frontend && npm start
   ```

3. **Test Igbo transcription:**
   - Go to Multi-Chat
   - Select "Igbo"
   - Click "Start Recording"
   - Speak Igbo
   - Verify text appears in Igbo

4. **(Optional) Set up Google Cloud for better accuracy**

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend Browser                     │
│  ┌─────────────────────────────────────────────────────┐ │
│  │         Web Speech API (Real-time)                  │ │
│  │  Input: Igbo speech  → Output: Igbo text (interim)  │ │
│  │  Language: ig-NG (BCP 47)                           │ │
│  └─────────────────────────────────────────────────────┘ │
│                     ↓ (Stop Recording)                    │
│  ┌─────────────────────────────────────────────────────┐ │
│  │      Send Audio + Language to Backend               │ │
│  │      POST /api/multiperson/multiperson-diarize      │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                        Backend                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │         perform_speech_to_text()                    │ │
│  │  Language: 'igbo' → Maps to:                        │ │
│  │    • Google Cloud: 'ig-NG'                          │ │
│  │    • NaijaVox: 'igbo'                               │ │
│  │    • ElevenLabs: 'ig'                               │ │
│  └─────────────────────────────────────────────────────┘ │
│                          ↓ Service Priority              │
│  ┌──────────────────────────────────────────────────┐    │
│  │  1. Google Cloud → 2. NaijaVox → 3. ElevenLabs  │    │
│  └──────────────────────────────────────────────────┘    │
│                          ↓                               │
│  ┌─────────────────────────────────────────────────────┐ │
│  │    ✅ Return: Igbo Text (not translated)            │ │
│  └─────────────────────────────────────────────────────┘ │
│                          ↓                               │
│  ┌─────────────────────────────────────────────────────┐ │
│  │   perform_speaker_diarization()                     │ │
│  │   Identify speakers: Speaker 1, Speaker 2, etc.    │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Return to Frontend                          │
│  {                                                       │
│    "success": true,                                      │
│    "conversations": [                                    │
│      {                                                   │
│        "participant": "Speaker 1",                       │
│        "originalText": "Kedu? Mma onwe gị?",            │
│        "translatedText": "Hi? How are you?",            │
│        "timestamp": "00:00"                              │
│      }                                                   │
│    ]                                                     │
│  }                                                       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│            Display in Multi-Chat Tab                    │
│  Speaker 1: "Kedu? Mma onwe gị?" [IGBO]                │
│             🌐 English ▶                                 │
│             ✓ English ▼  "Hi? How are you?"             │
└─────────────────────────────────────────────────────────┘
```

---

## Summary

| Feature | Status | Setup Time |
|---------|--------|-----------|
| Real-time Igbo transcription (browser) | ✅ Ready | 0 min |
| NaijaVox-2.0 Igbo STT | ✅ Ready | 0 min* |
| Google Cloud Igbo STT | ⭕ Optional | 15 min |
| ElevenLabs Igbo STT | ✅ Ready | 0 min |
| Speaker diarization | ✅ Ready | 0 min |
| Igbo↔English translation | ✅ Ready | 0 min |

\* First use downloads model (~2.5GB, ~5-10 min)

---

## Questions?

- **NaijaVox not working?** → Run `python test_igbo_stt.py`
- **Want better accuracy?** → Set up Google Cloud (see Option 2)
- **Audio upload failing?** → Check file size/format (WAV, MP3, OGG)
- **Speed too slow?** → Enable GPU: `NAIJAVOX_DEVICE=cuda`
