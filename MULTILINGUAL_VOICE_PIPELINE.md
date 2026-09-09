# 🎤 Complete Multilingual Voice Pipeline Guide

## Overview

The app now supports a **complete end-to-end voice processing pipeline** for Nigerian languages:

```
🎤 Voice Input (Igbo/Yoruba/Hausa)
    ↓
📝 Transcription (NaijaVox-2.0 STT) → Display on screen
    ↓
🌍 Translation to English (Google Translate)
    ↓
🤖 LLM Processing (Get AI response)
    ↓
🌍 Translation back to original language
    ↓
🔊 Text-to-Speech output (Audio or Text)
```

---

## 🚀 Quick Start (5 minutes)

### 1. **Install Dependencies**

```bash
cd backend
pip install google-cloud-texttospeech google-cloud-translate google-cloud-speech
pip install transformers torch torchaudio librosa pydub
```

### 2. **Set Up Google Cloud Credentials**

The pipeline uses **Google Cloud APIs** for best quality. You need ONE service account with these permissions:

1. Go to https://console.cloud.google.com
2. Create a new project: "brainr"
3. Enable these APIs:
   - `Speech-to-Text API` (speech.googleapis.com)
   - `Text-to-Speech API` (texttospeech.googleapis.com)
   - `Translation API` (translate.googleapis.com)
4. Create a Service Account with these roles:
   - `Cloud Speech-to-Text Admin`
   - `Cloud Text-to-Speech User`
   - `Cloud Translation API Editor`
5. Download JSON key file
6. Save to: `backend/credentials/google-multilingual-key.json`

### 3. **Update Configuration**

Edit `backend/.env`:

```env
# Google Cloud credentials (single file for all services)
GOOGLE_CLOUD_STT_CREDENTIALS_PATH=credentials/google-multilingual-key.json
GOOGLE_CLOUD_TTS_CREDENTIALS_PATH=credentials/google-multilingual-key.json
GOOGLE_CLOUD_TRANSLATION_CREDENTIALS_PATH=credentials/google-multilingual-key.json

# Or use environment variable (simpler)
export GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials/google-multilingual-key.json
```

### 4. **Start the Backend**

```bash
cd backend
python run.py
```

The app will automatically:
- Download NaijaVox-2.0 from HuggingFace (~2.5GB, cached)
- Prepare Google Cloud clients for STT, TTS, Translation

### 5. **Test the Pipeline**

Use Postman or curl:

```bash
curl -X POST http://localhost:5001/api/voice/process \
  -F "audio=@sample_igbo.wav" \
  -F "language=igbo" \
  -F "instructions=Translate this to English and summarize" \
  -F "return_audio=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "success": true,
  "language": "igbo",
  "original_transcription": "Kedu ka ị mara? Ọ dị mma.",
  "english_transcription": "How are you? I'm fine.",
  "llm_response_english": "You're greeting someone and saying you're doing well. This is a polite introduction in Igbo.",
  "llm_response_translated": "Ị na-ekele mmadụ ka ị sị na ị dị mma. Nke a bụ ihu mma nke mkpọ okwu na Igbo.",
  "audio_response": "base64-encoded MP3...",
  "steps": [...]
}
```

---

## 📱 API Endpoints

### 1. **Complete Voice Processing** (Primary)

**POST** `/api/voice/process`

Handles the entire pipeline: transcription → translation → LLM → translation → TTS

**Request (multipart/form-data):**
```
audio              (file)    - Required. Audio file (WAV, MP3, OGG, FLAC)
language           (string)  - Required. Language: igbo, yoruba, hausa, pidgin, english
instructions       (string)  - Required. What should AI do with transcription
return_audio       (bool)    - Optional. Return audio response (default: false)
voice_gender       (string)  - Optional. MALE, FEMALE, NEUTRAL (default: NEUTRAL)
```

**Response:**
```json
{
  "success": boolean,
  "language": "igbo",
  "original_transcription": "User's speech transcribed in original language",
  "english_transcription": "Translated to English",
  "llm_response_english": "AI response in English",
  "llm_response_translated": "AI response in original language",
  "audio_response": "base64-encoded MP3 (if return_audio=true)",
  "steps": [
    { "step": 1, "name": "Audio Transcription", "status": "✓", "result": "..." },
    { "step": 2, "name": "Translate to English", "status": "✓", "result": "..." },
    ...
  ]
}
```

### 2. **Test Transcription Only**

**POST** `/api/voice/test-transcription`

Test audio transcription without LLM processing.

**Request (multipart/form-data):**
```
audio     (file)    - Audio file
language  (string)  - Language code
```

**Response:**
```json
{
  "success": true,
  "language": "igbo",
  "transcription": "Transcribed text in Igbo",
  "english_translation": "English translation"
}
```

### 3. **Test Translation**

**POST** `/api/voice/test-translation`

Test text translation between any supported languages.

**Request (JSON):**
```json
{
  "text": "Text to translate",
  "source_language": "igbo",
  "target_language": "english"
}
```

**Response:**
```json
{
  "success": true,
  "original_text": "Kedu ka ị mara?",
  "translated_text": "How are you?",
  "source_language": "igbo",
  "target_language": "english"
}
```

### 4. **Test Text-to-Speech**

**POST** `/api/voice/test-tts`

Test audio synthesis for any language and text.

**Request (JSON):**
```json
{
  "text": "Kedu ka ị mara?",
  "language": "igbo",
  "voice_gender": "NEUTRAL"
}
```

**Response:**
```json
{
  "success": true,
  "language": "igbo",
  "audio_response": "base64-encoded MP3...",
  "message": "Audio synthesis successful for igbo"
}
```

### 5. **Get Supported Languages**

**GET** `/api/voice/languages`

Get list of supported languages and details.

**Response:**
```json
{
  "success": true,
  "languages": ["igbo", "yoruba", "hausa", "pidgin", "english"],
  "details": {
    "igbo": { "display": "Igbo", "native": "Igbo", "country": "Nigeria" },
    "yoruba": { "display": "Yoruba", "native": "Yoruba", "country": "Nigeria" },
    ...
  }
}
```

---

## 🔧 Component Details

### Speech-to-Text (STT) - NaijaVox-2.0 + Google Cloud

**Primary:** NaijaVox-2.0 (HuggingFace)
- Best WER (Word Error Rate) for Nigerian languages: **22.58%**
- Languages: Igbo, Yoruba, Hausa, Nigerian Pidgin, Nigerian English
- Model downloads automatically (~2.5GB cached)
- Runs on GPU if available, CPU fallback

**Fallback:** Google Cloud Speech-to-Text
- More reliable for noisy environments
- Better punctuation
- Requires API credentials

**Automatic Selection:**
1. NaijaVox-2.0 (for Nigerian languages)
2. Google Cloud (if credentials available)
3. OpenAI Whisper (if OPENAI_API_KEY set)
4. Mock transcription (testing fallback)

### Translation - Google Cloud + LLM

**Primary:** Google Cloud Translation API
- Real-time, professional-quality translation
- Supports all 4+ languages including rare African languages
- Cost: ~$0.002 per 100 words

**Fallback:** LLM-based translation
- Uses your configured LLM (Gemini, OpenAI, etc.)
- Zero API cost if LLM already configured
- Good quality but slightly slower

**Languages Supported:**
- Igbo (ig)
- Yoruba (yo)
- Hausa (ha)
- Nigerian Pidgin (pcm)
- English (en)

### Text-to-Speech (TTS) - Google Cloud

**Service:** Google Cloud Text-to-Speech
- High-quality, natural-sounding voices
- Supports all Nigerian languages with native speakers
- Multiple voice options (MALE, FEMALE, NEUTRAL)
- Cost: ~$0.004 per 1,000 characters

**Output Format:** MP3 (base64-encoded in API responses)

**Voice Options:**
- MALE: Deep, professional voice
- FEMALE: Clear, friendly voice
- NEUTRAL: Balanced voice

### LLM Processing

**Uses your configured LLM:**
- Gemini (default)
- OpenAI GPT-4
- Anthropic Claude
- Local HuggingFace models

The English transcription is sent to the LLM with user instructions for processing.

---

## 💾 Data Flow

```
User uploads Igbo audio file
    ↓
NaijaVox-2.0 transcribes → "Kedu ka ị mara?"
    ↓
Google Translate → English: "How are you?"
    ↓
LLM processes with instructions → English response
    ↓
Google Translate → Back to Igbo
    ↓
Google TTS → MP3 audio file
    ↓
Response sent to user (text + audio if requested)
```

### Performance

**Typical Times:**
- Transcription: 2-5 seconds (depends on audio length)
- Translation: 0.5-1 second (both directions)
- LLM Processing: 1-3 seconds (depends on response length)
- TTS: 1-2 seconds
- **Total:** ~5-12 seconds end-to-end

---

## 🐛 Troubleshooting

### Issue: NaijaVox Model Not Downloading

**Solution:**
```bash
# Manually download model
python -c "
from transformers import WhisperForConditionalGeneration, WhisperProcessor
model = WhisperForConditionalGeneration.from_pretrained('Axiveri/NaijaVox-2.0')
processor = WhisperProcessor.from_pretrained('Axiveri/NaijaVox-2.0')
print('Model downloaded successfully!')
"
```

### Issue: "Credentials not found"

**Solution:**
1. Check .env file has `GOOGLE_CLOUD_STT_CREDENTIALS_PATH` set
2. Verify credentials file exists: `credentials/google-multilingual-key.json`
3. Or set environment variable:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
   ```

### Issue: Translation Returns English (Fallback)

**Cause:** Google Cloud Translation API not configured or failed
- Check credentials path in .env
- Verify service account has `translate.googleapis.com` permission
- Check quota in Google Cloud Console

**Workaround:** LLM translation will be used automatically

### Issue: TTS Audio Not Generated

**Cause:** Google Cloud TTS not configured
- Check TTS credentials path in .env
- Verify service account has `texttospeech.googleapis.com` permission
- App will return text response instead

**Workaround:** Use browser TTS or configure Google Cloud TTS

### Issue: Poor Transcription Quality

**Try:**
1. Record in quiet environment (no background noise)
2. Speak clearly and loudly
3. Ensure audio is minimum 2-3 seconds
4. Use better quality microphone

**If still poor:**
- Use Google Cloud STT instead (configure credentials)
- NaijaVox is optimized for Nigerian-accented speech

---

## 🔐 Security & Privacy

- Audio files are uploaded to your backend server
- Only used for transcription, not stored permanently
- Deleted immediately after processing
- Translation happens server-side or via Google Cloud
- No data sent to external services except Google Cloud (if configured)

**Recommendations:**
- Use HTTPS for all audio uploads
- Implement rate limiting on voice endpoints
- Store credentials in secure location (not in git)
- Use environment variables for sensitive data

---

## 📊 Cost Analysis

### Using Google Cloud (Recommended)

**Per-minute costs:**
- STT: ~$0.024/min (~$1.44/hour)
- TTS: ~$0.004 per 1,000 chars (~$0.24 for 60-minute audio)
- Translation: ~$0.002 per 100 words (~$0.24 for 12,000 words)

**Total per hour:** ~$1.90

**Free Tier:**
- Google Cloud free tier: $300 credit for first 90 days
- Enough for ~157 hours of full pipeline usage

### Using NaijaVox + LLM (Offline)

**Costs:**
- NaijaVox: FREE (runs locally)
- LLM: Only if using paid API (Gemini, OpenAI, etc.)
- TTS: FREE (use browser TTS)

**Best for low-cost, offline deployment**

---

## 📚 Resources

- [NaijaVox-2.0 Model](https://huggingface.co/Axiveri/NaijaVox-2.0)
- [Google Cloud Speech-to-Text](https://cloud.google.com/speech-to-text/docs)
- [Google Cloud Text-to-Speech](https://cloud.google.com/text-to-speech/docs)
- [Google Cloud Translation](https://cloud.google.com/translate/docs)

---

## ✅ Checklist: Getting Production Ready

- [ ] Google Cloud credentials file created and saved
- [ ] All three APIs enabled in Google Cloud Console (STT, TTS, Translation)
- [ ] .env file updated with credentials paths
- [ ] NaijaVox model downloaded (or auto-download tested)
- [ ] Test endpoint `/api/voice/languages` returns 200
- [ ] Test transcription with `/api/voice/test-transcription`
- [ ] Test translation with `/api/voice/test-translation`
- [ ] Test TTS with `/api/voice/test-tts`
- [ ] Full pipeline test with `/api/voice/process`
- [ ] Audio quality verified with multiple recordings
- [ ] Error handling tested (missing credentials, bad audio, etc.)
- [ ] Performance monitored (times recorded in logs)

---

## 🎯 Next Steps

1. **Frontend Integration**: Update UI to use `/api/voice/process` endpoint
2. **Streaming Audio**: Implement WebSocket for real-time transcription
3. **Multi-speaker Support**: Add speaker diarization to transcription
4. **Custom LLM Prompts**: Allow users to create custom AI instructions
5. **Audio Caching**: Cache translated audio to reduce TTS costs
6. **Offline Mode**: Use local TTS for zero-cost deployment
