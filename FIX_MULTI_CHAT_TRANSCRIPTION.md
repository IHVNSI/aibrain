# 🚀 Multi-Chat Transcription - Fix & Test Guide

**Objective:** Get real Igbo transcription (not mock) in Multi-Chat  
**Estimated Time:** 15 minutes

---

## 🎯 Quick Start

### Step 1: Restart Backend with Logging (2 min)

```bash
cd backend
python run.py > stt_debug.log 2>&1
```

**Keep this terminal open** - you'll check the logs after recording.

### Step 2: Restart Frontend (1 min)

In another terminal:
```bash
cd frontend
npm start
```

### Step 3: Test Recording (5 min)

1. Open app in browser: http://localhost:5173
2. Go to **Multi-Chat** tab
3. ✅ Check: "Auto-detect speakers"
4. Select: **Igbo** (language dropdown)
5. Click: **Start Recording**
6. Speak slowly and clearly:
   - **"Kedu? Mma onwe gị?"** (Hello? How are you?)
   - Or any Igbo phrase
   - Speak for **at least 2-3 seconds**
7. Click: **Stop Recording**
8. **Wait 10-30 seconds** (first time loads model)

### Step 4: Check Results (7 min)

#### ✅ If you see Igbo text displayed:
```
🎉 SUCCESS! Your Igbo STT is working!
```
Go to [Celebration Section](#-celebration) below.

#### ❌ If you still see mock transcript:
```
Speaker 100:00
This is a test conversation.

Speaker 201:00
Yes, let's proceed with the discussion.
```

Go to [Troubleshooting Section](#-troubleshooting) below.

---

## 🎉 Celebration
<If you see your Igbo text, you're done!>

Your Multi-Chat transcription is now working! You can:
- ✅ Speak Igbo naturally
- ✅ See real-time transcription in Igbo
- ✅ Multiple speakers detected automatically
- ✅ English translation on-demand

**Next:** Try with Yoruba or Hausa too!

---

## 🔧 Troubleshooting

### Problem 1: Still Seeing Mock Transcript

**Check the backend logs:**

```bash
# In the terminal where you ran "python run.py":
# Scroll up to see the logs, or:
tail -50 stt_debug.log
```

**Look for one of these errors:**

#### Error A: "Audio file is empty"
```
❌ Audio file is empty (0 bytes) - no audio was recorded
```

**Cause:** Microphone not recording  
**Fix:**
1. Check browser microphone permissions:
   - Windows: Settings → Privacy & Security → App permissions → Microphone
   - macOS: System Preferences → Security & Privacy → Microphone
2. Allow app to use microphone
3. Close browser completely
4. Reopen browser
5. Try recording again

#### Error B: "NaijaVox dependencies not installed"
```
❌ NaijaVox dependencies not installed: No module named 'transformers'
   Install with: pip install transformers torch librosa torchaudio
```

**Cause:** Missing Python packages  
**Fix:**
```bash
pip install transformers torch librosa torchaudio --upgrade
```

Then restart backend:
```bash
cd backend
python run.py > stt_debug.log 2>&1
```

#### Error C: "Audio too short"
```
❌ Audio too short (0.3s) - need at least 0.5 seconds
```

**Cause:** Recorded too short  
**Fix:**
- Record for **at least 1-2 seconds**
- Speak in full sentences: "Kedu? Mma onwe gị?"

#### Error D: "Audio array is empty"
```
❌ NaijaVox: Audio array is empty - audio file may be corrupted
```

**Cause:** Audio file corrupted or invalid format  
**Fix:**
1. Try uploading a known-good audio file
2. Try a different browser
3. Restart your computer's audio

### Problem 2: "Still loading..." for too long

**Expected behavior:**
- First run: 5-10 minutes (downloading ~2.5GB model)
- Subsequent runs: 2-5 seconds

**Check progress:**
```bash
# In terminal, you should see:
⬇️  Downloading model (first time, ~2.5GB)...
[Wait...]
✅ NaijaVox-2.0 model loaded successfully
```

**If it says "still loading" after 15 minutes:**
1. Check internet connection
2. Check disk space (need ~5GB free)
3. Try restarting backend

### Problem 3: Browser showing microphone error

**In browser console (F12 → Console), you see:**
```
❌ Microphone error: ...
```

**Fix:**
1. Close browser completely
2. Go to browser settings → Clear all data
3. Reopen browser
4. Grant microphone permission when asked
5. Try again

### Problem 4: Seeing error: "Only admins can use this feature"

**Cause:** Your account is not an admin  
**Fix:**
```bash
cd backend
python setup_admin.py
# Then log back in
```

---

## 📋 Diagnostic Checklist

Work through these in order:

- [ ] **Audio Recording**
  - [ ] Microphone shows in browser settings
  - [ ] "Start Recording" button works
  - [ ] Browser doesn't show permission error
  - [ ] Can speak clearly for 2+ seconds

- [ ] **Backend Logs** 
  - [ ] Terminal shows: `📁 Audio file saved: ... (5000+ bytes)`
  - [ ] NOT showing: "Audio file is empty"
  - [ ] NOT showing: "Audio too short"

- [ ] **Python Dependencies**
  ```bash
  python -c "import transformers, torch, librosa; print('✅ All packages installed')"
  ```
  - [ ] Output: `✅ All packages installed`
  - [ ] If error, run: `pip install transformers torch librosa`

- [ ] **Backend Logs - STT Pipeline**
  - [ ] Shows: `🎯 STT Pipeline Started`
  - [ ] Shows: `2️⃣  Trying: NaijaVox-2.0...`
  - [ ] Shows: `✅ NaijaVox-2.0 success: XX chars for Igbo`
  - [ ] NOT showing: `❌ FAILED: NaijaVox`

- [ ] **Frontend Displays Result**
  - [ ] NOT showing mock: "Speaker 1: This is a test conversation"
  - [ ] Showing: Your actual Igbo text
  - [ ] Shows number of speakers detected

---

## 🧪 Testing Scenarios

### Test 1: With Microphone (Recommended)
1. Go to Multi-Chat
2. Select "Igbo"
3. Click "Start Recording"
4. Speak: "Kedu? Mma onwe gị? Kem ka ị nwere akụ?"
5. Click "Stop Recording"
6. **Expected:** See Igbo text displayed

### Test 2: With Audio File Upload
1. Download sample Igbo audio (or use any audio)
2. Go to Multi-Chat
3. Click "Upload Audio File"
4. Select file
5. **Expected:** See transcription in Igbo

### Test 3: With English (Baseline)
1. Go to Multi-Chat
2. Select "English"
3. Record: "Hello, how are you? I'm doing great!"
4. **Expected:** See English text
5. **If this works:** Problem is Igbo-specific, try upgrading NaijaVox
6. **If this fails too:** General STT infrastructure issue

### Test 4: Direct Python Test
```bash
python test_igbo_stt.py
```

**Expected output:**
```
✅ All dependencies installed
✅ NaijaVox service available
✅ Web Speech API language codes correct
```

---

## 🆘 Still Not Working?

### Quick Fix: Force NaijaVox to Run Now

Test NaijaVox directly (ignores all fallbacks):

```bash
cd backend

# Create test script
cat > test_naijavox_direct.py << 'EOF'
import sys
sys.path.insert(0, 'app')
from api.multiperson_chat import _transcribe_with_naijavox
import tempfile
import wave
import os

# Create a test WAV file
temp_dir = tempfile.gettempdir()
test_wav = os.path.join(temp_dir, 'test.wav')

# Create silent test WAV (valid but empty)
with wave.open(test_wav, 'wb') as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(16000)
    f.writeframes(b'\x00' * 32000)  # 1 second of silence

# Test NaijaVox
print("Testing NaijaVox directly...")
result = _transcribe_with_naijavox(test_wav, 'igbo', 'Igbo')
print(f"Result: {result}")
print(f"Status: {'✅ Working' if result else '❌ Failed'}")
EOF

python test_naijavox_direct.py
```

**If this fails**, copy the error message and share it.

---

## 📞 Need More Help?

Provide this information:

1. **Backend logs (last 50 lines):**
   ```bash
   tail -50 stt_debug.log
   ```

2. **Python version:**
   ```bash
   python --version
   ```

3. **Package versions:**
   ```bash
   pip show transformers torch librosa
   ```

4. **OS:**
   - Windows 10/11?
   - macOS?
   - Linux?

5. **Browser:**
   - Chrome?
   - Firefox?
   - Edge?

6. **Microphone:**
   - Inbuilt?
   - USB mic?
   - Headset?

---

## ✅ Success Indicators

When working correctly, you should see in logs:

```
=====================================================================
🎯 STT Pipeline Started
   Language: igbo (Nigerian: True)
   File: /tmp/audio_xxx.wav (85432 bytes)
   Model: naijavox
=====================================================================
2️⃣  Trying: NaijaVox-2.0 (FREE, optimized for Nigerian languages)...
🚀 NaijaVox-2.0: Initializing for Igbo...
   Device: cpu
   Dtype: float16
♻️  Using cached NaijaVox-2.0 model
🎵 Loading audio from /tmp/audio_xxx.wav...
✅ Audio loaded: 170000 samples at 16000Hz
🎯 Preparing language tokens for igbo...
✅ Language tokens prepared
🔊 Preprocessing audio...
✅ Audio preprocessed: torch.Size([1, 80, 3200])
💬 Running NaijaVox-2.0 inference...
✅ Inference complete
📝 Decoding output to text...
✅ Decoded: Kedu? Mma onwe gị? Kem ka ị nwere akụ? ...
✅ NaijaVox-2.0 success: 78 chars for Igbo
✅ SUCCESS: NaijaVox-2.0 - 78 chars
✓ Detected 1 speaker(s) and 1 statement(s)
```

---

## 🎓 Understanding the Pipeline

```
You speak Igbo
    ↓
🎤 Browser captures audio (MediaRecorder)
    ↓
📤 Sends audio blob to backend
    ↓
✅ Backend validates audio file (not empty, valid format)
    ↓
🚀 Attempts STT services in order:
    1. Google Cloud (not configured) ⏭️
    2. NaijaVox-2.0 (FREE, tries here!) ← Should work
       - Downloads model (first time, 5-10 min)
       - Loads audio with librosa
       - Prepares language tokens
       - Runs inference with transformers
       - Returns Igbo text ✅
    3. ElevenLabs (skipped)
    4. Mock (fallback if all fail)
    ↓
📥 Returns transcript with speaker detection
    ↓
💬 Frontend displays Igbo text
```

---

## 🎬 Demo Recording Script

When everything works, test with this exact script:

1. Click "Start Recording"
2. Speak exactly: "Kedu ka ị ha? Mma onwe gị?"
3. Click "Stop Recording"
4. Expected: See Igbo transcription
5. 🎉 Success!

---

**Status:** Ready to debug  
**Next:** Follow "Step 1: Restart Backend with Logging" above

Good luck! 🍀
