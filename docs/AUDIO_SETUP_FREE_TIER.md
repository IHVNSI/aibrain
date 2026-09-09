# Audio Setup Without Google Cloud - Free Alternatives

Since you don't have Google Cloud billing, here are the audio features you can use **completely free**:

## ✅ What Works WITHOUT Google Cloud

### Speech-to-Text (STT) - Free Options:

#### 1. **NaijaVox-2.0** (Best for Nigerian Languages)
- **Cost:** FREE (one-time ~2.5GB download)
- **Supported Languages:** Yoruba, Hausa, Igbo, Nigerian Pidgin, Nigerian English
- **Setup:** Automatic on first use
- **Configuration in .env:**
  ```env
  NAIJAVOX_DEVICE=auto
  NAIJAVOX_TORCH_DTYPE=float16
  ```
- **Pros:** Completely free, local, optimized for African languages
- **Cons:** Slower on CPU (faster on GPU)

#### 2. **OpenAI Whisper** (General Multilingual)
- **Cost:** Included with existing OPENAI_API_KEY
- **Supported Languages:** All languages including Igbo, Yoruba, Hausa
- **Status:** Already configured (OPENAI_API_KEY is set in .env)
- **Pros:** Excellent accuracy, multilingual
- **Cons:** Requires internet, uses API quota

### Text-to-Speech (TTS) - Free Options:

#### 1. **Browser Native TTS**
- **Cost:** FREE (built-in to all browsers)
- **Supported Languages:** Varies by browser, typically English and major languages
- **Quality:** Basic, system voices
- **Pros:** No server needed, zero latency, no API calls
- **Cons:** Limited language support (mainly English)

---

## ⚠️ What Needs Google Cloud or Paid Service

### Text-to-Speech for African Languages (Igbo, Yoruba, Hausa):

The challenge: Getting high-quality TTS in African languages typically requires:
- **Google Cloud Text-to-Speech** (paid service, needs billing account)
- **ElevenLabs** (premium service, $5-99/month)

### Workaround Solution for Now:

For testing and demonstration, you can:
1. Use **OpenAI Whisper** for transcription (free with your existing key)
2. Use **NaijaVox-2.0** for STT (free, local)
3. For African language TTS output, use **browser fallback** with English text (not perfect but functional)

---

## 🚀 Recommended Setup (Free Tier)

Add these to your `.env` file:

```env
# ===== STT Configuration =====
# Default to NaijaVox for Nigerian languages
# Will fallback to Whisper if NaijaVox isn't available

# NaijaVox-2.0 Settings (completely free)
NAIJAVOX_DEVICE=auto          # or 'cpu' if no GPU
NAIJAVOX_TORCH_DTYPE=float16  # float16 for faster inference

# ===== TTS Configuration =====
# Browser TTS will be used for English (no server setup needed)
# For African languages, you'll need Google Cloud or ElevenLabs

# Leave these empty - they're not available without paid service
GOOGLE_CLOUD_TTS_CREDENTIALS_PATH=
ELEVENLABS_API_KEY=
```

---

## 📋 Step-by-Step Setup (No Google Cloud)

### 1. Verify OpenAI API Key
Check that `OPENAI_API_KEY` is set in `.env`:
```bash
grep "OPENAI_API_KEY" backend/.env
```
Should show: `OPENAI_API_KEY=sk-proj-...`

### 2. Install NaijaVox Dependencies
```bash
cd backend
pip install librosa torchaudio transformers torch
```

### 3. Update .env
```bash
# Edit backend/.env and ensure:
NAIJAVOX_DEVICE=auto
NAIJAVOX_TORCH_DTYPE=float16
```

### 4. Test STT (Speech-to-Text)
The first time you test NaijaVox, it will download the model (~2.5GB):
```bash
python
>>> from transformers import AutoModelForCTC
>>> model = AutoModelForCTC.from_pretrained('Axiveri/NaijaVox-2.0')
# Wait for download to complete...
```

### 5. Start the Backend
```bash
python run.py
```

### 6. Test in UI
- Open Settings → Audio tab
- Go to **Speech-to-Text** section
- Select "NaijaVox-2.0"
- Click "Test STT"
- Should return transcription (or try with a voice recording)

---

## 📊 Feature Matrix - Free Setup

| Feature | Status | Notes |
|---------|--------|-------|
| **STT in English** | ✅ | OpenAI Whisper |
| **STT in Igbo** | ✅ | NaijaVox-2.0 or Whisper |
| **STT in Yoruba** | ✅ | NaijaVox-2.0 or Whisper |
| **STT in Hausa** | ✅ | NaijaVox-2.0 or Whisper |
| **TTS in English** | ✅ | Browser native |
| **TTS in Igbo** | ❌ | Requires Google Cloud or paid service |
| **TTS in Yoruba** | ❌ | Requires Google Cloud or paid service |
| **TTS in Hausa** | ❌ | Requires Google Cloud or paid service |
| **Voice Training** | ✅ | Record samples locally |

---

## 🔧 Testing Without Full Audio

You can still test the **STT** features by:

1. **Using Whisper API:**
   - Settings → Audio → Speech-to-Text
   - Select "OpenAI Whisper"
   - Click "Test STT"
   - Transcription will work

2. **Using NaijaVox-2.0:**
   - Settings → Audio → Speech-to-Text
   - Select "NaijaVox-2.0"
   - Click "Test STT"
   - Will work for Nigerian languages

3. **Recording Voice Samples:**
   - Settings → Audio → Voice Training
   - Click "Record Voice Sample"
   - Samples stored locally for speaker identification

---

## 🎯 Future Options When Ready

### Option 1: Enable Google Cloud (Paid)
- Estimated cost: $15-20/month for typical usage
- Provides high-quality TTS for all languages
- Follow [Audio Configuration Setup](AUDIO_CONFIGURATION_SETUP.md)

### Option 2: Use ElevenLabs (Paid)
- Estimated cost: $5-99/month
- Premium voices with cloning
- More accessible than Google Cloud setup

### Option 3: Community Options
- Contribute voice samples to open TTS projects
- Use community-built African language TTS models
- Support for more models can be added in future updates

---

## 📝 Implementation Notes

The audio system is designed to gracefully handle missing services:
- ✅ Frontend shows status for each service
- ✅ Backend returns clear error messages
- ✅ Users can test what's available
- ✅ Fallback to browser TTS for English
- ✅ No crashes if Google Cloud is unavailable

---

## 🆘 Troubleshooting

### Issue: "NaijaVox model not found"
**Solution:** It will auto-download on first use. Ensure you have ~2.5GB free disk space.

### Issue: "Whisper API rate limited"
**Solution:** You're hitting the OpenAI API quota. Wait a bit or upgrade your plan.

### Issue: "Test TTS shows error for Igbo/Yoruba/Hausa"
**Expected:** This is expected without Google Cloud. The system is working correctly by showing what's unavailable.

### Issue: "Browser TTS doesn't play audio"
**Solution:** Check browser console (F12) for errors, ensure browser has microphone permission.

---

## 📞 Next Steps

1. **Complete STT setup** - NaijaVox + Whisper will cover transcription
2. **Test voice training** - Record samples for speaker identification
3. **Plan for TTS** - When budget allows, enable Google Cloud or ElevenLabs
4. **Monitor usage** - Keep track of Whisper API usage

The application is fully functional for **voice input transcription** right now. TTS for African languages is the only limitation without paid services, but **browser TTS works for English**, which is a good starting point.

---

For detailed setup of Google Cloud (when ready), see: [AUDIO_CONFIGURATION_SETUP.md](AUDIO_CONFIGURATION_SETUP.md)
