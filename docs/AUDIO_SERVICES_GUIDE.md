# 🎙️ Audio Services Configuration Guide

Complete setup guide for all supported STT and TTS services.

---

## 📋 Quick Overview

| Service | Type | Cost | Setup Complexity | Quality |
|---------|------|------|------------------|---------|
| **Browser Native** | TTS | Free | ✅ None (built-in) | Good |
| **Web Speech API** | STT | Free | ✅ None (browser) | Good |
| **NaijaVox-2.0** | STT | Free | 🟡 Medium | Good |
| **OpenAI Whisper** | STT | $0.02/min | 🟡 Medium | Excellent |
| **Google Chirp TTS** | TTS | ~$1/1M chars | 🟠 Hard | Excellent |
| **Google Cloud TTS** | TTS | ~$15/1M chars | 🟠 Hard | Premium |
| **Google Cloud STT** | STT | $0.006/15s | 🟠 Hard | Excellent |
| **Azure TTS** | TTS | Free-$1/hr | 🟠 Hard | Excellent |
| **Azure STT** | STT | Free-$1/hr | 🟠 Hard | Excellent |
| **ElevenLabs TTS** | TTS | $5-99/mo | 🟠 Hard | Premium |
| **ElevenLabs Scribe** | STT | Premium | 🟠 Hard | Premium |

---

## 🚀 FREE Services (Recommended Start)

### 1️⃣ Browser Native TTS (English)
**Status:** ✅ Always available (no setup needed)

**Features:**
- Free, local, built-in
- English only
- Offline capable
- No API key required

**How to use:**
1. Settings → Audio → Text-to-Speech
2. Select "Browser Native TTS"
3. Language: English
4. Click "Test TTS"

---

### 2️⃣ Web Speech API (STT in any language)
**Status:** ✅ Always available (browser-based)

**Features:**
- Free, local, built-in
- Works in Chrome, Edge, Safari
- All languages supported
- Offline capable
- No API key required

**How to use:**
1. Settings → Audio → Speech-to-Text
2. Select "Web Speech API"
3. Choose language
4. Click "Test STT"

---

### 3️⃣ NaijaVox-2.0 (STT for African languages)
**Status:** ✅ Recommended for Nigerian languages

**Supported Languages:**
- English
- Igbo
- Yoruba
- Hausa
- Nigerian Pidgin

**Cost:** Free (local, no API needed)

**Setup:**
```bash
# Install dependencies
pip install librosa torchaudio transformers torch

# Optional GPU acceleration
pip install torch --index-url https://download.pytorch.org/whl/cu118  # CUDA 11.8
```

**First Run:**
- NaijaVox will download ~2.5GB model on first use
- Cached for future runs
- Requires internet only for first download

**How to use:**
1. Settings → Audio → Speech-to-Text
2. Select "NaijaVox-2.0"
3. Choose African language
4. Click "Test STT"

---

## 💳 Affordable Services ($1-5 setup)

### 4️⃣ OpenAI Whisper (Multilingual STT)
**Status:** ✅ Already configured (if OPENAI_API_KEY set)

**Cost:** $0.02 per minute

**Features:**
- Excellent multilingual support
- Handles African languages well
- Pay-as-you-go

**Setup:**
```bash
# 1. Get API key from https://platform.openai.com/api-keys
# 2. Add to .env
OPENAI_API_KEY=sk-...
```

**How to use:**
1. Settings → Audio → Speech-to-Text
2. Select "OpenAI Whisper (Large-v3)"
3. Choose language
4. Click "Test STT"

---

## ☁️ Cloud Services (Recommended for Production)

### 5️⃣ Google Cloud Text-to-Speech (Premium TTS)
**Cost:** ~$15 per 1M characters (or Chirp for ~$1/1M)

#### Setup Google Cloud Account

**Step 1: Create GCP Project**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project (Project name: "brainr-audio")
3. Enable billing

**Step 2: Enable APIs**
1. Search "Text-to-Speech API" → Enable
2. Search "Speech-to-Text API" → Enable
3. Search "Cloud Translation API" → Enable

**Step 3: Create Service Account**
1. Navigation → IAM & Admin → Service Accounts
2. Create Service Account
3. Grant these roles:
   - Cloud Text-to-Speech Client
   - Cloud Speech-to-Text Client
   - Cloud Translation User
4. Create JSON key
5. Download and save securely

**Step 4: Configure Environment**
```bash
# Save JSON key to secure location
mkdir -p ~/.gcp
cp /path/to/service-account-key.json ~/.gcp/credentials.json

# Add to backend/.env
GOOGLE_CLOUD_TTS_CREDENTIALS_PATH=/home/user/.gcp/credentials.json
GOOGLE_CLOUD_STT_CREDENTIALS_PATH=/home/user/.gcp/credentials.json
GOOGLE_CLOUD_TRANSLATION_CREDENTIALS_PATH=/home/user/.gcp/credentials.json
```

**How to use:**
1. Settings → Audio → Text-to-Speech
2. Select "Google Cloud Text-to-Speech" or "Google Chirp TTS"
3. Choose language (all languages work!)
4. Click "Test TTS"

---

### 6️⃣ Azure Speech Services
**Cost:** Free tier (5M characters/month) or $1/hour

#### Setup Azure

**Step 1: Create Azure Account**
1. Go to [Azure Portal](https://portal.azure.com/)
2. Create Speech resource
3. Region: East US or other
4. Pricing tier: Free (F0) or Standard (S0)

**Step 2: Get Credentials**
1. Open created resource
2. Click "Keys and Endpoint"
3. Copy Key 1 and Region

**Step 3: Configure Environment**
```bash
# Add to backend/.env
AZURE_SPEECH_KEY=your_key_here
AZURE_SPEECH_REGION=eastus
```

**Install SDK:**
```bash
pip install azure-cognitiveservices-speech
```

**How to use:**
1. Settings → Audio → Text-to-Speech or Speech-to-Text
2. Select "Azure Text-to-Speech" or "Azure Speech-to-Text"
3. Choose language
4. Click "Test"

---

### 7️⃣ ElevenLabs Premium Voices
**Cost:** $5-99/month depending on plan

#### Setup ElevenLabs

**Step 1: Create Account**
1. Go to [ElevenLabs](https://elevenlabs.io/)
2. Sign up free account
3. Verify email

**Step 2: Get API Key**
1. Profile → API Keys
2. Copy API key

**Step 3: Configure Environment**
```bash
# Add to backend/.env
ELEVENLABS_API_KEY=your_api_key_here
```

**Install SDK:**
```bash
pip install elevenlabs
```

**How to use:**
1. Settings → Audio → Text-to-Speech or Speech-to-Text
2. Select "ElevenLabs Text-to-Speech" or "ElevenLabs Scribe API"
3. Choose language
4. Click "Test"

---

## 🧪 Testing Audio Services

### Test Any Service

In Settings → Audio tab, you can test individual services:

**For STT (Speech-to-Text):**
1. Select STT tab
2. Choose a model from dropdown
3. Select language
4. Click "Test STT"
5. See status: ✅ working or ❌ not configured

**For TTS (Text-to-Speech):**
1. Select TTS tab
2. Choose a model from dropdown
3. Select language
4. Click "Test TTS"
5. Hear audio output or see error

---

## 📊 Recommended Configuration by Use Case

### 📱 Mobile/Light Use
```
STT: Web Speech API (free, offline)
TTS: Browser Native (free, English only)
Total Cost: $0
```

### 🏢 Small Team
```
STT: NaijaVox-2.0 (free local) + Whisper ($0.02/min backup)
TTS: Browser Native (free) + Azure TTS (Free tier)
Total Cost: $5 setup (Azure) + usage

.env config:
OPENAI_API_KEY=sk-...
AZURE_SPEECH_KEY=key...
AZURE_SPEECH_REGION=eastus
```

### 🏭 Production (African Languages)
```
STT: Google Cloud Speech-to-Text ($0.006/15s)
TTS: Google Chirp TTS (~$1/1M chars)
Both: Google Cloud Service Account + Free tier
Translation: Google Cloud Translation API

.env config:
GOOGLE_CLOUD_TTS_CREDENTIALS_PATH=~/.gcp/credentials.json
GOOGLE_CLOUD_STT_CREDENTIALS_PATH=~/.gcp/credentials.json
```

### 🎙️ Premium Audio
```
STT: ElevenLabs Scribe + Whisper
TTS: ElevenLabs Text-to-Speech (voice cloning)
Cost: ~$100/month

.env config:
ELEVENLABS_API_KEY=key...
OPENAI_API_KEY=sk-...
```

---

## 🔧 Troubleshooting

### "Service not configured"
- Verify API key/credentials in .env
- Check file paths exist
- Restart backend after .env changes

### "Import error" (e.g., google-cloud-texttospeech not found)
```bash
# Install missing library
pip install google-cloud-texttospeech

# Or for Azure
pip install azure-cognitiveservices-speech

# Or for ElevenLabs
pip install elevenlabs
```

### Audio plays but sounds robotic
- Try different gender settings
- Switch to Google Chirp or ElevenLabs for better quality
- Adjust pitch/rate sliders

### "Authentication failed"
- Verify credentials path is correct
- Check permissions on .env file
- Ensure service account has required roles

---

## 📚 External Documentation

- [Google Cloud Text-to-Speech](https://cloud.google.com/text-to-speech/docs)
- [Google Cloud Speech-to-Text](https://cloud.google.com/speech-to-text/docs)
- [Azure Speech Services](https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/)
- [ElevenLabs API](https://elevenlabs.io/docs)
- [OpenAI Whisper](https://platform.openai.com/docs/guides/speech-to-text)

---

## ✅ Next Steps

1. **Start with FREE services** (Browser TTS + Web Speech API)
2. **Test NaijaVox-2.0** for African language STT
3. **Add Whisper** ($0.02/min, excellent quality)
4. **Upgrade to cloud services** (Google/Azure) when ready for production
5. **Use ElevenLabs** for premium audio quality and voice cloning

All services can be tested and switched in Settings → Audio → Test buttons! 🎉
