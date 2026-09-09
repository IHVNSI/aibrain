# Audio Configuration Setup Guide

This guide explains how to configure Speech-to-Text (STT) and Text-to-Speech (TTS) services for the Brainr application, especially for African languages (Igbo, Yoruba, Hausa, Nigerian Pidgin).

## Overview

The audio system supports multiple STT and TTS providers:

### Speech-to-Text (STT) Options:
1. **NaijaVox-2.0** (Local, Free) - Best for Nigerian languages
2. **OpenAI Whisper** (Cloud) - General purpose multilingual
3. **Google Cloud Speech-to-Text** (Cloud) - Best for African languages
4. **ElevenLabs Scribe API** (Premium) - Includes diarization

### Text-to-Speech (TTS) Options:
1. **Google Cloud Text-to-Speech** (Cloud) - **RECOMMENDED** for African languages
2. **ElevenLabs Text-to-Speech** (Premium) - Premium voices with cloning
3. **Browser Native TTS** (Local) - English only, no server needed

## Quick Start

### For English Only Testing:
No additional setup needed. The browser's built-in Web Speech Synthesis API will be used.

### For African Languages (Igbo, Yoruba, Hausa):
You need to configure **Google Cloud Text-to-Speech** API. Follow the steps below.

---

## Step 1: Set Up Google Cloud Service Account

### 1.1 Create a Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing one)
3. Enable the following APIs:
   - **Text-to-Speech API** (texttospeech.googleapis.com) - Required for voice synthesis
   - **Speech-to-Text API** (speech.googleapis.com) - Optional for STT
   - **Translation API** (translate.googleapis.com) - Optional for language translation

### 1.2 Create a Service Account
1. Go to **IAM & Admin** → **Service Accounts**
2. Click **Create Service Account**
3. Fill in details:
   - Service account name: `brainr-audio`
   - Description: "Service account for Brainr audio services"
4. Click **Create and Continue**
5. Grant roles:
   - Select **Editor** role (or more specific roles below)
   - Specific roles needed:
     - `roles/texttospeech.client` - For TTS
     - `roles/speech.client` - For STT
     - `roles/cloudtranslate.user` - For translation (optional)
6. Click **Continue** then **Done**

### 1.3 Create and Download Service Account JSON Key
1. Click on the created service account
2. Go to **Keys** tab
3. Click **Add Key** → **Create new key**
4. Select **JSON** format
5. Click **Create**
6. Save the file (e.g., `google-cloud-key.json`)
7. **Important:** Store this file securely (don't commit to version control)

---

## Step 2: Configure Environment Variables

### Option A: Using Credentials Path (Recommended)

1. **Place the JSON key file in a secure location:**
   ```bash
   # Example: Create a credentials directory
   mkdir -p ~/.gcp
   cp google-cloud-key.json ~/.gcp/google-cloud-key.json
   chmod 600 ~/.gcp/google-cloud-key.json
   ```

2. **Update `.env` file in `backend/` folder:**
   ```env
   # Google Cloud Credentials
   GOOGLE_CLOUD_TTS_CREDENTIALS_PATH=/home/username/.gcp/google-cloud-key.json
   GOOGLE_CLOUD_STT_CREDENTIALS_PATH=/home/username/.gcp/google-cloud-key.json
   GOOGLE_CLOUD_TRANSLATION_CREDENTIALS_PATH=/home/username/.gcp/google-cloud-key.json
   ```

### Option B: Using GOOGLE_APPLICATION_CREDENTIALS (Alternative)

You can set the environment variable globally:
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/home/username/.gcp/google-cloud-key.json
```

Then in `.env`:
```env
# Leave paths empty if using GOOGLE_APPLICATION_CREDENTIALS environment variable
GOOGLE_CLOUD_TTS_CREDENTIALS_PATH=
GOOGLE_CLOUD_STT_CREDENTIALS_PATH=
```

---

## Step 3: Configure NaijaVox-2.0 (Optional for Local STT)

NaijaVox-2.0 is a free, local speech recognition model optimized for Nigerian languages.

### 3.1 Install Required Dependencies
```bash
cd backend
pip install torch transformers librosa torchaudio
```

### 3.2 Update `.env` Configuration
```env
# NaijaVox-2.0 Configuration
NAIJAVOX_DEVICE=auto  # or 'cuda' for GPU, 'cpu' for CPU-only
NAIJAVOX_TORCH_DTYPE=float16  # float16 for faster inference, float32 for precision
```

**Note:** First use will download ~2.5GB model file. This is cached for future use.

---

## Step 4: Configure OpenAI Whisper (Optional for General STT)

If you want to use OpenAI Whisper as a fallback STT:

1. Ensure `OPENAI_API_KEY` is already set in `.env`:
   ```env
   OPENAI_API_KEY=sk-proj-YOUR-KEY-HERE
   ```

2. The application will automatically fall back to Whisper if NaijaVox is unavailable

---

## Step 5: Configure ElevenLabs (Optional for Premium Features)

For premium voice cloning and diarization:

1. Get API key from [ElevenLabs](https://elevenlabs.io/)
2. Add to `.env`:
   ```env
   ELEVENLABS_API_KEY=your-api-key-here
   ```

**Note:** ElevenLabs integration is marked as DEFERRED. Basic structure exists but full implementation is pending.

---

## Step 6: Restart the Application

After updating `.env` file, restart the backend:

```bash
# Kill the running Flask server
# Start fresh
cd backend
python run.py
```

---

## Step 7: Test Audio Configuration

1. Open the application in your browser
2. Go to **Settings** → **Audio** tab
3. You'll see the new **AudioConfigPanel** with tabs:
   - **Overview** - Quick status and language selection
   - **Speech-to-Text** - STT model configuration
   - **Text-to-Speech** - TTS model configuration
   - **Voice Training** - Enroll voice samples for speaker identification

4. Click **Test STT** or **Test TTS** buttons to verify setup
5. Select different languages and test audio output

---

## Supported Languages and Locale Codes

| Language | Code | STT | TTS | Notes |
|----------|------|-----|-----|-------|
| English | en-US | ✓ | ✓ | Default |
| Igbo | ig-NG | ✓ | ✓ | Nigerian Igbo |
| Hausa | ha-NG | ✓ | ✓ | Nigerian Hausa |
| Yoruba | yo-NG | ✓ | ✓ | Nigerian Yoruba |
| Nigerian Pidgin | pcm | ✓ | ~ | Pidgin transcription supported |

---

## Troubleshooting

### Issue: "Google Cloud Text-to-Speech not configured"

**Solution:** 
- Verify `GOOGLE_CLOUD_TTS_CREDENTIALS_PATH` is set in `.env`
- Check file path is correct and readable: `ls -la /path/to/key.json`
- Ensure JSON key has `type: "service_account"`
- Restart backend server

### Issue: Test buttons don't produce audio

**Solution:**
1. Check browser console for errors (F12 → Console)
2. Check backend logs: `tail backend.log`
3. Verify API endpoint is responding:
   ```bash
   curl -X POST http://localhost:5001/api/chat/synthesize-speech \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello", "language": "english"}'
   ```

### Issue: "Permission denied" when loading credentials

**Solution:**
```bash
# Fix file permissions
chmod 600 ~/.gcp/google-cloud-key.json

# Verify ownership
ls -l ~/.gcp/google-cloud-key.json
```

### Issue: NaijaVox model download failing

**Solution:**
```bash
# Check disk space (needs ~2.5GB)
df -h

# Set custom cache directory in .env if needed:
# NAIJAVOX_CACHE_DIR=/path/with/more/space

# Or manually download:
python -c "from transformers import AutoModelForCTC; AutoModelForCTC.from_pretrained('Axiveri/NaijaVox-2.0')"
```

### Issue: "CORS" or "401 Unauthorized" errors

**Solution:**
1. Verify API key is correct and not expired
2. Check that service account has proper permissions
3. Verify credentials file is not corrupted
4. Try a fresh credentials download from Google Cloud Console

---

## Pricing & Cost Estimation

### Google Cloud
- **Speech-to-Text:** ~$0.006 per 15 seconds (first 60 minutes free)
- **Text-to-Speech:** ~$15 per 1 million characters
- **Translation:** ~$15 per 1 million characters

### ElevenLabs
- Premium plans start at $5-99/month with usage allowances

### Local Options (Free)
- **NaijaVox-2.0:** Completely free after first download (~2.5GB)
- **Browser TTS:** Free, built-in to all browsers

---

## Best Practices

1. **Security:**
   - Never commit credentials to version control
   - Add `google-cloud-*.json` to `.gitignore`
   - Rotate service account keys periodically
   - Restrict service account permissions to only needed APIs

2. **Performance:**
   - Use `float16` for NaijaVox on GPU for faster inference
   - Cache downloaded models locally
   - Consider batch processing for multiple requests

3. **Cost Optimization:**
   - Use local NaijaVox-2.0 for STT when possible
   - Implement caching for repeated TTS requests
   - Monitor API usage in Google Cloud Console
   - Set up budget alerts

---

## References

- [Google Cloud Text-to-Speech Documentation](https://cloud.google.com/text-to-speech/docs)
- [Google Cloud Speech-to-Text Documentation](https://cloud.google.com/speech-to-text/docs)
- [NaijaVox-2.0 Model](https://huggingface.co/Axiveri/NaijaVox-2.0)
- [OpenAI Whisper Documentation](https://platform.openai.com/docs/guides/speech-to-text)
- [ElevenLabs Documentation](https://elevenlabs.io/docs)

---

## Support

If you encounter issues:

1. Check the **Audio** settings tab status indicators
2. Enable debug logging: Set `FLASK_DEBUG=1` in `.env`
3. Check backend logs for detailed error messages
4. Consult the troubleshooting section above
5. Refer to provider-specific documentation (Google Cloud, ElevenLabs, etc.)

