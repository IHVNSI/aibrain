# Speech-to-Text (STT) Setup Guide

## Quick Start: Which Service Should You Use?

| Service | Best For | Setup Time | Cost | African Languages |
|---------|----------|-----------|------|-------------------|
| **Google Cloud** | 🏆 RECOMMENDED - Best accuracy for African languages | 15 min | Pay-as-you-go (~$0.024/min) | ✅ Igbo, Yoruba, Hausa |
| **OpenAI Whisper** | Fallback - Works but lower accuracy for African languages | 5 min | Pay-as-you-go (~$0.06/min) | ⚠️ Works but limited |
| **Local Whisper** | Offline mode - No API costs, local processing | 20 min | Free (but requires compute) | ✅ Works locally |

**Current Setup**: The app will automatically try in this order:
1. Google Cloud Speech-to-Text (if configured)
2. OpenAI Whisper API (if configured)
3. Local Whisper model (if installed)
4. Mock transcripts (fallback for testing)

---

## ✅ RECOMMENDED: Google Cloud Speech-to-Text Setup

### Why Google Cloud?
- **Best support for African languages**: Native support for Igbo (ig-NG), Yoruba (yo-NG), Hausa (ha-NG)
- **Higher accuracy**: Especially for regional accents and dialects
- **Automatic punctuation**: Adds proper punctuation to transcripts
- **Enhanced models**: Better handling of technical terms and background noise
- **Speaker diarization ready**: Works well with the multi-speaker feature

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Create Project"** (or select existing project)
3. Name it: `brainr-speech-to-text` (or any name you prefer)
4. Click **Create**
5. Wait for project to be created (~30 seconds)

### Step 2: Enable Speech-to-Text API

1. In Cloud Console, search for **"Speech-to-Text API"**
2. Click **Speech-to-Text API** from results
3. Click **Enable**
4. Wait for API to be enabled

### Step 3: Create Service Account

1. Go to **IAM & Admin** → **Service Accounts**
2. Click **Create Service Account**
3. Fill in details:
   - **Service account name**: `brainr-stt`
   - **Service account ID**: Auto-populated (keep as is)
   - Click **Create and Continue**
4. On the next screen, click **Create Key**
5. Choose **JSON** format
6. Click **Create**
7. A JSON file will download automatically

### Step 4: Configure Backend

1. **Save the JSON key file** to your backend directory:
   ```bash
   # Create a credentials folder
   mkdir backend/credentials
   
   # Move the downloaded JSON file there
   mv ~/Downloads/brainr-stt-*.json backend/credentials/google-stt-key.json
   ```

2. **Update `.env` file** in the `backend/` folder:
   ```bash
   # Add this line:
   GOOGLE_CLOUD_STT_CREDENTIALS_PATH=credentials/google-stt-key.json
   ```
   
   Or alternatively, use the environment variable:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/full/path/to/backend/credentials/google-stt-key.json
   ```

### Step 5: Install Required Package

```bash
cd backend

# Activate virtual environment (if not already active)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Google Cloud Speech-to-Text library
pip install google-cloud-speech>=2.21
```

### Step 6: Test the Setup

Run the app:
```bash
cd backend
python run.py
```

Upload an audio file in the Multi-Chat interface. Check the backend logs:
- ✅ **Success**: `✓ Transcribed with Google Cloud (ig-NG): XXX chars`
- ❌ **Fallback**: `Google Cloud STT error...` (will try Whisper)

---

## Alternative 1: OpenAI Whisper (Fallback)

Whisper is already configured as a fallback. No additional setup needed if you have `OPENAI_API_KEY` in `.env`.

**Advantages:**
- Simple setup (1 API key)
- Works without additional dependencies

**Disadvantages:**
- Lower accuracy for African languages (less training data)
- Slightly slower (~1-2s per audio file)
- Higher cost (~$0.06/min vs $0.024/min for Google Cloud)

---

## Alternative 2: Local Whisper (Offline Mode)

For offline deployment or to avoid API costs:

### Installation

```bash
cd backend

# Install local Whisper
pip install openai-whisper

# Download model (one-time)
# Options: tiny (39M), base (74M), small (244M), medium (769M), large (2.9G)
# For African languages, use 'medium' or 'large' for best accuracy

python -m whisper --model large /path/to/sample/audio.wav

# This downloads the model to ~/.cache/whisper/
```

### Configuration

Update `.env`:
```bash
LOCAL_STT_MODEL_PATH=large
```

Or use full path:
```bash
LOCAL_STT_MODEL_PATH=/home/user/.cache/whisper/large.pt
```

### Benefits
- ✅ No API costs
- ✅ Works offline
- ✅ Faster than cloud API (GPU-accelerated)
- ✅ No rate limits

### Drawbacks
- ❌ Requires download (2.9GB for large model)
- ❌ Needs GPU for good performance (CPU is slow)
- ❌ Lower accuracy than Google Cloud for African languages

---

## Configuration Priority

The app tries services in this order:

```python
if GOOGLE_CLOUD_STT_CREDENTIALS_PATH or GOOGLE_APPLICATION_CREDENTIALS:
    ✓ Try Google Cloud
    → if fails → Try Whisper
else if OPENAI_API_KEY:
    ✓ Try Whisper
    → if fails → Try Local Whisper
else if LOCAL_STT_MODEL_PATH:
    ✓ Try Local Whisper
    → if fails → Use Mock Transcripts
else:
    ⚠ Use Mock Transcripts (testing only)
```

---

## Language Support

### Google Cloud Speech-to-Text
- **Igbo**: `ig-NG` (Nigerian Igbo) ⭐ Excellent
- **Yoruba**: `yo-NG` (Nigerian Yoruba) ⭐ Excellent
- **Hausa**: `ha-NG` (Nigerian Hausa) ⭐ Excellent
- **English**: `en-US`, `en-GB`, etc. ⭐ Excellent
- Plus 100+ other languages

### OpenAI Whisper
- **Igbo**: `ig` ⚠️ Limited
- **Yoruba**: `yo` ⚠️ Limited
- **Hausa**: `ha` ⚠️ Limited
- **English**: `en` ⭐ Excellent
- 99 languages total (but with varying accuracy)

### Local Whisper
- Supports same languages as Whisper API
- Quality depends on model size (larger = better)

---

## Troubleshooting

### "GOOGLE_APPLICATION_CREDENTIALS not configured"
**Solution**: Set the environment variable or update `.env`:
```bash
# Option 1: Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Option 2: Update .env
GOOGLE_CLOUD_STT_CREDENTIALS_PATH=credentials/google-stt-key.json
```

### "google-cloud-speech not installed"
**Solution**:
```bash
pip install google-cloud-speech>=2.21
```

### Audio transcription returns empty
**Solution**:
1. Check audio format (should be WAV, MP3, FLAC, or OGG)
2. Check audio duration (must be > 0 seconds)
3. Check audio quality (loud enough background speech)
4. Check language is correctly selected
5. Try Google Cloud directly to test credentials

### Google Cloud says "Permission denied"
**Solution**:
1. Verify JSON key file is in correct location
2. Verify `GOOGLE_CLOUD_STT_CREDENTIALS_PATH` is correct path
3. Check file permissions: `chmod 644 credentials/google-stt-key.json`
4. Try setting `GOOGLE_APPLICATION_CREDENTIALS` environment variable directly

### High costs?
**Solution**:
- Use local Whisper for offline/testing
- Reduce audio file sizes (shorter clips)
- Use voice activity detection to skip silent portions
- Consider bulk pricing for production

---

## Cost Estimation

### Google Cloud Speech-to-Text
```
$0.024 per minute of audio (standard model)
$0.048 per minute of audio (enhanced model)

Example costs:
- 10 min conversation: ~$0.24
- 1 hour conversation: ~$1.44
- 100 conversations (10 min avg): ~$24/month
```

### OpenAI Whisper
```
$0.006 per minute of audio

Example costs:
- 10 min conversation: ~$0.06
- 1 hour conversation: ~$0.36
- 100 conversations (10 min avg): ~$6/month
```

### Local Whisper
```
$0 (just compute cost if using GPU)
Initial download: 2.9GB
```

---

## Advanced: Custom Language Models

For even better African language support, consider:

### Option 1: Fine-tuned Google Cloud Model
- Train on domain-specific vocabulary (names, technical terms)
- Improves accuracy for your specific use case
- Estimated cost: $300-500 for training

### Option 2: N-ATLaS-LLM (African Languages)
- Purpose-built for African languages
- Supports: Amharic, Hausa, Igbo, Somali, Swahili, Tigrinya, Yoruba
- Free but requires local setup
- Repository: https://github.com/uonlrnr/n-atlas-llm

### Option 3: Fine-tuned Whisper
- Use Whisper API fine-tuning (coming soon)
- Train on African language audio samples
- Better accuracy than base Whisper

---

## FAQ

**Q: Which service should I use for production?**
A: Google Cloud Speech-to-Text. It has the best accuracy for African languages and reasonable costs ($0.024/min).

**Q: Can I use multiple services simultaneously?**
A: Yes! Configure Google Cloud as primary and Whisper as fallback. App will automatically use whichever is available.

**Q: How long does speech-to-text take?**
A: Usually 2-5 seconds for a 10-minute audio file. Processing time depends on audio duration and network latency.

**Q: Can I test without configuring an API?**
A: Yes! The app will use mock transcripts for testing. Just record audio and see the mock transcript appear. But real speech-to-text requires API configuration.

**Q: Does speech-to-text work offline?**
A: Only with local Whisper. Google Cloud and OpenAI Whisper require internet.

**Q: Will speech-to-text transcribe speaker names?**
A: No, it transcribes what was said. Speaker diarization (identifying different speakers) happens separately in the AI instructions step.

---

## Next Steps

1. ✅ Choose a service (recommended: Google Cloud)
2. ✅ Set up credentials
3. ✅ Update `.env` file
4. ✅ Install required packages: `pip install -r requirements.txt`
5. ✅ Test with audio upload in Multi-Chat interface
6. ✅ Check backend logs for success/error messages

Happy transcribing! 🎤
