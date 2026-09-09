# NaijaVox-2.0 Setup Guide: Nigerian Language Speech Recognition

## Overview

**NaijaVox-2.0** is an open-weight automatic speech recognition (ASR) model specifically trained for Nigerian languages. It's now fully integrated into the brainr app for superior Nigerian language speech-to-text capabilities.

### What is NaijaVox-2.0?

- **Model**: Axiveri/NaijaVox-2.0 from Hugging Face
- **Base**: OpenAI Whisper-large-v3 with PEFT LoRA fine-tuning
- **License**: Apache 2.0 (Open Source)
- **Training Data**: 25,866 samples across 7 datasets
- **Accuracy**: 22.58% average WER (77.62% relative improvement over V1)
- **Training Method**: LoRA fine-tuning (r=64, targeting attention + feed-forward layers)
- **Robustness**: SpecAugment + Realistic noise augmentation (30% of training data)

### Supported Languages

| Language | Code | Support | Features |
|----------|------|---------|----------|
| 🇳🇬 Yoruba | `yoruba` | ⭐⭐⭐⭐⭐ | Full diacritics (ẹ, ọ, ṣ, à, á, etc.) |
| 🇳🇬 Hausa | `hausa` | ⭐⭐⭐⭐⭐ | Special chars (ƙ, ƴ, ɗ, etc.) |
| 🇳🇬 Igbo | `igbo` | ⭐⭐⭐⭐⭐ | Full diacritics |
| 🇳🇬 Nigerian Pidgin | `pidgin` | ⭐⭐⭐⭐⭐ | Creole English (code-switching aware) |
| 🇳🇬 Nigerian English | `english` | ⭐⭐⭐⭐ | Nigerian-accented English |

### Performance Metrics

Benchmark results on identical test sets (50 samples/language):

| Language | WER (V2) | WER Reduction | Relative Improvement |
|----------|---------|---------------|----------------------|
| Yoruba | 22.3% | ↓ 6.5pp | +22.6% |
| Hausa | 25.8% | ↓ 5.2pp | +16.8% |
| Igbo | 30.5% | ↓ 11.4pp | +27.2% 🏆 |
| Nigerian Pidgin | 14.7% | ↓ 2.1pp | +12.5% |
| Nigerian English | 19.6% | ↓ 1.5pp | +7.1% |
| **Average** | **22.58%** | **↓ 5.3pp** | **+19.1%** |

---

## Installation & Setup

### Step 1: Install Dependencies

The required packages are already listed in `backend/requirements.txt`:

```bash
cd backend

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install/update dependencies
pip install -r requirements.txt
```

Required packages for NaijaVox:
- `transformers>=4.44` - Model loading and inference
- `torch>=2.2` - PyTorch (GPU support if available)
- `torchaudio>=2.0` - Audio processing
- `librosa>=0.10` - Audio feature extraction

### Step 2: Configuration (Optional)

The app auto-detects the best setup. For optimal performance, configure in `backend/.env`:

```bash
# Auto-detect device (CUDA if available, else CPU)
NAIJAVOX_DEVICE=auto

# For GPU: use float16 (faster, less memory) or float32 (precise)
# For CPU: use float32 (default)
NAIJAVOX_TORCH_DTYPE=float16

# Optional: Custom model cache directory
# NAIJAVOX_CACHE_DIR=/path/to/cache
```

### Step 3: First Run

```bash
# Start the app
python run.py
```

**On first run**, the NaijaVox-2.0 model (~2.5GB) will be automatically downloaded from Hugging Face and cached locally:
- **Location**: `~/.cache/huggingface/hub/models--Axiveri--NaijaVox-2.0/`
- **Time**: 5-10 minutes depending on internet speed
- **Subsequent runs**: Use cached model (instant)

### Step 4: Test the Setup

1. Go to **Settings → Audio**
2. Select **"NaijaVox-2.0 (Nigerian Languages)"** as your STT model
3. Choose your preferred language (Yoruba, Hausa, Igbo, Pidgin, Nigerian English)
4. Click **"Test Audio"** to verify everything works

**Expected output**: 
```
✓ Transcribed with NaijaVox-2.0: XXX chars
```

---

## Usage Guide

### In the App

#### Settings → Audio Tab

1. **Speech-to-Text Model**: Select `NaijaVox-2.0 (Nigerian Languages)`
2. **Voice Input Language**: Choose your preferred language
3. **Test Audio**: Click to verify audio input/output

#### Multi-Chat Interface

1. Click the **Microphone icon** in the chat
2. Speak in your selected language
3. Audio is automatically transcribed using NaijaVox
4. Text is processed by the LLM
5. Response is synthesized to audio (if enabled)

### Via API

The app automatically selects NaijaVox for Nigerian languages:

```python
# In your code:
# For Nigerian languages, the app will automatically use NaijaVox
# No additional configuration needed!

# The flow is:
# English → Uses selected model (Whisper/NaijaVox/etc)
# Igbo/Yoruba/Hausa/Pidgin → Automatically uses NaijaVox if available
```

---

## Performance Optimization

### GPU Acceleration (Recommended for Production)

If you have an NVIDIA GPU:

```bash
# Install CUDA-enabled PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Update .env
NAIJAVOX_DEVICE=cuda
NAIJAVOX_TORCH_DTYPE=float16  # For faster inference + less memory
```

**GPU Performance**:
- **Input**: 10-minute audio
- **Time**: ~10-15 seconds (with float16)
- **Memory**: ~4-6GB VRAM

### CPU Processing

NaijaVox works on CPU but is slower:

```bash
NAIJAVOX_DEVICE=cpu
NAIJAVOX_TORCH_DTYPE=float32  # More stable on CPU
```

**CPU Performance**:
- **Input**: 10-minute audio
- **Time**: ~2-5 minutes (depending on CPU)
- **Memory**: ~8-12GB RAM

### Model Caching

The model is automatically cached after first download. To clear cache:

```bash
# Clear Hugging Face cache
rm -rf ~/.cache/huggingface/hub/models--Axiveri--NaijaVox-2.0/

# On Windows:
rmdir /s %USERPROFILE%\.cache\huggingface\hub\models--Axiveri--NaijaVox-2.0\
```

---

## Advanced Features

### Code-Switching Support

NaijaVox is trained on code-switching patterns found in everyday Nigerian speech. It can handle:

```
Speaker: "Na true, the network connection e don slow. O kwa, we need better infrastructure."
Transcript: "Na true, the network connection e don slow. Okay, we need better infrastructure."
```

### Real-World Robustness

The model is trained with realistic Nigerian recording conditions:

- **Market noise**: Vendor voices, haggling, background commerce
- **Phone compression**: WhatsApp voice notes, call recordings
- **Outdoor ambient sound**: Traffic, crowds, environmental noise
- **Multiple speakers**: Natural conversations with overlapping speech

### Diarization (Multi-Speaker Support)

Combine NaijaVox with the built-in diarization feature:

1. Upload multi-speaker audio in Nigerian language
2. NaijaVox transcribes each speaker
3. Diarization assigns speaker labels
4. LLM summarizes or analyzes the conversation

---

## Troubleshooting

### Issue: "NaijaVox dependencies not installed"

**Solution**:
```bash
cd backend
pip install -r requirements.txt

# If librosa fails:
pip install --upgrade librosa
```

### Issue: Model download fails or hangs

**Solution**:
```bash
# 1. Check internet connection
# 2. Verify HuggingFace API is accessible
# 3. Set custom cache directory:

# In .env:
NAIJAVOX_CACHE_DIR=/path/to/custom/cache

# Or via environment:
export HF_HOME=/path/to/custom/cache
```

### Issue: "CUDA out of memory" error

**Solution 1**: Use CPU instead
```bash
NAIJAVOX_DEVICE=cpu
```

**Solution 2**: Use float32 instead of float16
```bash
NAIJAVOX_TORCH_DTYPE=float32
```

**Solution 3**: Reduce audio chunk size (in code)

### Issue: Empty or garbled transcription

**Possible causes**:
1. Audio quality too low (noisy background)
2. Audio sample rate not 16kHz
3. Language selection doesn't match audio
4. Model not fully loaded

**Solutions**:
```bash
# 1. Check audio quality (test with high-quality recording first)
# 2. Ensure language selection matches your speech
# 3. Check logs:
tail -f logs/app.log | grep NaijaVox
# 4. Restart app to reload model
```

### Issue: Slow inference time

**Solution**:
1. Use GPU if available
2. Use float16 instead of float32
3. Reduce concurrent requests (wait for previous transcription to finish)

---

## Integration with App Features

### Email Checking & Responses

NaijaVox transcribes voice commands in Nigerian languages for email management:

```
User (Yoruba): "Ka wo ni emails mi fun ojo yi" 
→ NaijaVox: "Check my emails for today"
→ App: Fetches and reads new emails
→ Response: "You have 5 new emails"
```

### Security & Permissions

NaijaVox respects the app's role-based security system:
- Admin can set STT model per user/role
- Language selection is user-specific
- Audio is processed securely with encryption

### Database Integration

All transcriptions are:
- Stored in audit logs (if enabled)
- Linked to user conversations
- Searchable by language
- Compliant with data retention policies

---

## API Reference

### Backend Function

```python
from app.api.multiperson_chat import perform_speech_to_text

# Auto-detect best model (NaijaVox for Nigerian languages)
transcript = perform_speech_to_text(
    audio_path="audio.wav",
    language="yoruba",  # or igbo, hausa, pidgin, english
    llm=llm_instance,
    stt_model='auto'  # or 'naijavox' to force it
)

# Force NaijaVox
transcript = perform_speech_to_text(
    audio_path="audio.wav",
    language="igbo",
    llm=llm_instance,
    stt_model='naijavox'
)
```

### Environment Variables

```bash
# Device
NAIJAVOX_DEVICE=cuda|cpu|auto          # Default: auto (GPU if available)

# Data type (GPU optimization)
NAIJAVOX_TORCH_DTYPE=float16|float32    # Default: float16 (GPU), float32 (CPU)

# Cache directory
NAIJAVOX_CACHE_DIR=/path/to/cache       # Default: ~/.cache/huggingface/
```

---

## Text-to-Speech Integration

While NaijaVox handles **speech-to-text**, the app uses these for **text-to-speech** in Nigerian languages:

### Available TTS Options

1. **Google Cloud Text-to-Speech**
   - Best quality for African languages
   - Supports Hausa, Yoruba, Igbo with native speakers
   - Paid service (~$16 per 1M characters)

2. **ElevenLabs**
   - High-quality multilingual voices
   - Premium service

3. **Local TTS Models** (Coming soon)
   - Free alternatives
   - Lower latency
   - Offline capable

---

## Combining STT + TTS

The brainr app creates a complete pipeline:

```
User (Nigerian Language)
    ↓
[NaijaVox-2.0 STT]  ← You are here
    ↓ (English text)
[LLM Processing]
    ↓
[TTS Response]  ← Add this
    ↓
User (Nigerian Language Audio)
```

---

## Best Practices

### ✅ Do's
- Use high-quality audio (clear speech, minimal background noise)
- Select the correct language before recording
- Keep audio files < 1GB for best performance
- Use GPU if processing large batches
- Cache the model for multiple calls

### ❌ Don'ts
- Don't mix languages in a single audio file (if using single-language model)
- Don't use extremely compressed/poor quality audio
- Don't process multiple files simultaneously on CPU (use queue system)
- Don't forget to activate virtual environment before running
- Don't leave large batch jobs running unattended

---

## FAQ

**Q: Is NaijaVox free?**
A: Yes! It's open-source under Apache 2.0 license. No API costs.

**Q: Does it work offline?**
A: Yes, after first download. The model is cached locally (~2.5GB).

**Q: Can I use it for commercial purposes?**
A: Yes, Apache 2.0 license allows commercial use.

**Q: How accurate is it compared to Google Cloud?**
A: For Nigerian languages, NaijaVox is comparable or better in some cases (e.g., Igbo: 30.5% WER vs Google's reported ~35% WER).

**Q: Can I fine-tune NaijaVox on my own data?**
A: Yes, the model supports further fine-tuning with your domain-specific data. See Hugging Face documentation.

**Q: Does it support code-switching?**
A: Yes, trained on code-switching patterns in Nigerian speech.

**Q: How do I report issues or contribute?**
A: Visit https://huggingface.co/Axiveri/NaijaVox-2.0

---

## Resources

- **Model Card**: https://huggingface.co/Axiveri/NaijaVox-2.0
- **GitHub**: https://github.com/Axiveri/NaijaVox
- **Creator**: Emmanuel Ariyo (Ememzyvisuals) - Axiveri
- **Citation**: See NaijaVox-2.0 model card for BibTeX

---

## Support

For issues specific to:
- **NaijaVox model**: https://huggingface.co/Axiveri/NaijaVox-2.0/discussions
- **brainr app integration**: Open an issue in the brainr repository
- **PyTorch/Transformers**: https://discuss.pytorch.org/

---

## Changelog

### Version 1.0 (2025-08-31)
- ✅ Initial integration of NaijaVox-2.0
- ✅ Auto-detection for Nigerian languages
- ✅ GPU/CPU support with optimization options
- ✅ Full diarization support
- ✅ Documentation and troubleshooting guides

