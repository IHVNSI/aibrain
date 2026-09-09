# 🔧 Multi-Chat Transcription Troubleshooting Guide

**Status:** Debugging comprehensive logging added  
**Date:** September 4, 2026

---

## Issue Summary

Your Multi-Chat is showing mock transcript instead of real speech transcription. This means:

✅ Audio IS being captured  
❌ But NOT being transcribed by any STT service  
⚠️  System is falling back to mock data

---

## Root Cause Analysis

The backend is trying STT services in this order:

```
1. Google Cloud (if configured)         ← SKIPPED (not configured)
2. NaijaVox-2.0 (FREE, optimized)       ← FAILING (need to debug)
3. ElevenLabs (if configured)           ← SKIPPED (not configured) 
4. Mock Transcript                      ← CURRENTLY USED ❌
```

**Most likely:** NaijaVox dependencies are missing or audio validation is failing

---

## 🔍 Step 1: Check Backend Logs

Start backend and capture detailed logs:

```bash
cd backend
python run.py > stt_debug.log 2>&1
```

Then record Igbo speech. Logs will show:

### If working ✅
```
=====================================================================
🎯 STT Pipeline Started
   Language: igbo (Nigerian: True)
   File: /tmp/audio_xxx.wav (12345 bytes)
   Model: naijavox
=====================================================================
2️⃣  Trying: NaijaVox-2.0 (FREE, optimized for Nigerian languages)...
🚀 NaijaVox-2.0: Initializing for Igbo...
   Device: cpu
   Dtype: float16
   ⬇️  Downloading model (first time, ~2.5GB)...
✅ NaijaVox-2.0 model loaded successfully
🎵 Loading audio from /tmp/audio_xxx.wav...
✅ Audio loaded: 160000 samples at 16000Hz
🎯 Preparing language tokens for igbo...
✅ Language tokens prepared
🔊 Preprocessing audio...
✅ Audio preprocessed: torch.Size([1, 80, 3000])
💬 Running NaijaVox-2.0 inference...
✅ Inference complete
📝 Decoding output to text...
✅ Decoded: Kedu? Mma onwe gị? ...
✅ NaijaVox-2.0 success: 45 chars for Igbo
✅ SUCCESS: NaijaVox-2.0 - 45 chars
```

### If failing ❌
```
2️⃣  Trying: NaijaVox-2.0 (FREE, optimized for Nigerian languages)...
❌ FAILED: NaijaVox: Audio file is empty (0 bytes)
```

Or:
```
❌ NaijaVox dependencies not installed: No module named 'transformers'
   Install with: pip install transformers torch librosa torchaudio
```

---

## 🔍 Step 2: Check Audio File Validation

Look for these errors in logs:

### Error 1: Audio file is empty
```
❌ Audio file is empty (0 bytes) - no audio was recorded
❌ NaijaVox: Audio array is empty - audio file may be corrupted
```

**Fix:**
- Ensure microphone is working
- Speak louder and for longer
- Try uploading an audio file instead of recording

### Error 2: Audio too short
```
❌ Audio too short (0.3s) - need at least 0.5 seconds
```

**Fix:**
- Record for at least 0.5 seconds
- Speak in Igbo: "Kedu? Mma onwe gị?"

### Error 3: Invalid WAV format
```
❌ Invalid WAV file: Error in parsing WAV header
```

**Fix:**
- Check browser microphone permissions
- Try a different browser
- Try uploading a known-good WAV file

---

## 🔍 Step 3: Check NaijaVox Dependencies

Run diagnostic:

```bash
python test_igbo_stt.py
```

Look for:
```
✅ transformers: 5.5.3
✅ torch: 2.11.0+cpu
✅ librosa: 1.0.0
✅ torchaudio: 2.11.0+cpu
```

### If missing:
```bash
pip install transformers torch librosa torchaudio
```

---

## 🔍 Step 4: Check Browser Microphone

In browser console (F12), run:

```javascript
// Check if Web Speech API is working
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
console.log('Web Speech API available:', !!SpeechRecognition);

// Check microphone permissions
navigator.mediaDevices.getUserMedia({audio: true})
  .then(stream => {
    console.log('✅ Microphone access granted');
    stream.getTracks().forEach(track => track.stop());
  })
  .catch(err => console.error('❌ Microphone error:', err));
```

Expected output:
```
✅ Web Speech API available: true
✅ Microphone access granted
```

---

## 🔍 Step 5: Check Frontend Audio Blob

Add this logging to MultiPersonChat.jsx (around line 70):

```javascript
const processAudioDiarization = async (audioBlob) => {
  console.log('📊 Audio Blob Details:');
  console.log('   Size:', audioBlob.size, 'bytes');
  console.log('   Type:', audioBlob.type);
  console.log('   Is empty:', audioBlob.size === 0);
  
  // ... rest of function
}
```

After recording, check browser console:

```
📊 Audio Blob Details:
   Size: 0 bytes         ← PROBLEM!
   Type: audio/wav
   Is empty: true
```

If size is 0, the MediaRecorder is not capturing audio. Try:
1. Check microphone permissions
2. Refresh browser
3. Try Chrome instead of Firefox
4. Restart OS audio

---

## 📋 Quick Debugging Checklist

- [ ] Backend logs show "Audio file is empty" → Problem: No audio recorded
- [ ] Backend logs show "NaijaVox dependencies not installed" → Solution: `pip install transformers torch librosa`
- [ ] Backend logs show "Audio too short" → Solution: Record longer
- [ ] Browser console shows "Microphone error" → Problem: Browser can't access mic
- [ ] `test_igbo_stt.py` shows missing packages → Solution: Install them
- [ ] Everything looks OK but still getting mock → Enable verbose logging (see below)

---

## 🚨 Advanced Debugging: Enable Verbose Logging

Edit `backend/.env` and add:

```env
FLASK_ENV=development
FLASK_DEBUG=1
LOG_LEVEL=DEBUG
```

Restart backend:
```bash
cd backend
python run.py
```

Now you'll see:
```
DEBUG: 🎵 Loading audio from /tmp/audio_xxx.wav...
DEBUG: ♻️  Using cached NaijaVox-2.0 model
DEBUG: 🎯 Preparing language tokens for igbo...
... (much more detail)
```

---

## 💡 Common Solutions

### Problem 1: Microphone Not Recording
```
❌ Audio file is empty (0 bytes)
```

**Solutions:**
1. Check browser microphone permissions:
   - Chrome: Settings → Privacy → Microphone → Allow
   - Firefox: Preferences → Privacy → Permissions → Microphone → Allow
2. Restart browser
3. Try: `navigator.mediaDevices.getUserMedia({audio: true})`
4. Check OS audio settings

### Problem 2: NaijaVox Not Loading
```
❌ NaijaVox dependencies not installed
```

**Solutions:**
```bash
pip install transformers torch librosa torchaudio --upgrade
python test_igbo_stt.py  # Verify
```

### Problem 3: Audio File Corrupted
```
❌ Invalid WAV file: Error in parsing WAV header
```

**Solutions:**
1. Try uploading a known-good WAV file
2. Try recording again
3. Check system audio settings
4. Try different browser

### Problem 4: Slow First Run
```
🚀 NaijaVox-2.0: Initializing for Igbo...
   ⬇️  Downloading model (first time, ~2.5GB)...
[Wait 5-10 minutes]
```

**Expected behavior:**
- First run: 5-10 minutes (model download)
- Subsequent runs: 2-5 seconds (cached model)
- This is normal! Let it finish

### Problem 5: Out of Memory
```
❌ NaijaVox: CUDA out of memory
```

**Solutions:**
```bash
# In .env, change:
NAIJAVOX_DEVICE=cpu     # Use CPU instead of GPU
NAIJAVOX_TORCH_DTYPE=float32  # Use more memory but compatible
```

Then restart backend.

---

## 📞 Getting Help

When reporting an issue, provide:

1. **Backend logs:**
   ```bash
   tail -100 stt_debug.log
   ```

2. **Browser console logs:**
   - Press F12
   - Go to Console tab
   - Screenshot the output

3. **Diagnostic output:**
   ```bash
   python test_igbo_stt.py
   ```

4. **System info:**
   - OS: Windows/Mac/Linux
   - Python version: `python --version`
   - GPU: `nvidia-smi` (if applicable)

---

## 🧪 Testing Scenarios

### Scenario 1: Test with Recorded File
Instead of microphone, upload a known-good audio file:
1. Download sample: [sample_igbo.wav](https://example.com/sample.wav)
2. Go to Multi-Chat
3. Click "Upload Audio File"
4. Select file
5. Check results

### Scenario 2: Test with English
1. Go to Multi-Chat
2. Select "English"
3. Record: "Hello, how are you?"
4. Check if English transcription works
5. If yes: NaijaVox might be the issue
6. If no: General STT infrastructure problem

### Scenario 3: Test NaijaVox Directly
```bash
python -c "
from app.api.multiperson_chat import _transcribe_with_naijavox
result = _transcribe_with_naijavox('sample.wav', 'igbo', 'Igbo')
print(f'Result: {result}')
"
```

---

## 📊 Expected vs Actual Behavior

### Expected ✅
```
Recording: "Kedu? Mma onwe gị?"
↓
Backend logs: "✅ NaijaVox-2.0 success: 45 chars for Igbo"
↓
Display: "Kedu? Mma onwe gị?" (in Igbo)
```

### Actual ❌
```
Recording: "Kedu? Mma onwe gị?"
↓
Backend logs: "❌ FAILED: NaijaVox - trying next service..."
↓
Display: "This is a test conversation." (mock)
```

---

## Next Steps

1. **Check logs:** `tail -100 stt_debug.log`
2. **Find the error** from the list above
3. **Apply fix** from Solutions section
4. **Test again:** Record in Multi-Chat
5. **Verify:** Should see actual Igbo text, not mock

**Ready?** Start backend with logging and try recording! 🎤

---

**Last Updated:** September 4, 2026  
**Created for:** Igbo STT Troubleshooting
