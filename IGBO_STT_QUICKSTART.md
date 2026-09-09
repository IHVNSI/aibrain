# 🚀 Quick Start: Igbo STT

## Test It Now (2 minutes)

```bash
# Terminal 1: Start backend
cd backend
python run.py

# Terminal 2: Start frontend  
cd frontend
npm start
```

Then in browser:
1. Go to **Multi-Chat** tab
2. Check "**Auto-detect speakers**"
3. Select language: "**Igbo**"
4. Click "**Start Recording**"
5. Speak Igbo: *"Kedu? Mma onwe gị?"*
6. **Stop Recording**
7. ✅ See Igbo text appear

---

## What's Working ✅

| Feature | Status |
|---------|--------|
| Real-time Igbo transcription | ✅ Browser-side (Web Speech API) |
| Backend Igbo transcription | ✅ NaijaVox-2.0 (FREE) |
| Yoruba & Hausa | ✅ Same support |
| Speaker detection | ✅ Auto-identified |
| English translation | ✅ On-demand |
| Audio file upload | ✅ Drag & drop |

---

## Service Priority

**For Igbo/Yoruba/Hausa:**
```
Google Cloud (if configured)
    ↓
NaijaVox-2.0 ← You are here ✅ FREE
    ↓
ElevenLabs (if configured)
    ↓
Mock (for testing)
```

---

## Setup Times

| Method | Time | Cost | Accuracy |
|--------|------|------|----------|
| NaijaVox | 0 min* | FREE | ⭐⭐⭐⭐ |
| Google Cloud | 15 min | $0.024/min | ⭐⭐⭐⭐⭐ |
| ElevenLabs | 0 min** | $0.003/min | ⭐⭐⭐⭐ |

*First use: 5-10 min model download  
**Already configured in .env

---

## Troubleshooting

### ❌ "No speech detected"
→ Speak louder, clearer, longer

### ❌ "Text in English not Igbo"
→ Check language dropdown, restart backend

### ❌ "Still loading..."
→ First use downloads model (5-10 min), normal

### ❌ "Memory error"
→ Already optimized, try on machine with more RAM

### ✅ All working?
→ Try: `python test_igbo_stt.py`

---

## .env Check

```
# Should be set:
NAIJAVOX_DEVICE=auto              ✅
NAIJAVOX_TORCH_DTYPE=float16       ✅
ELEVENLABS_API_KEY=sk_...          ✅
OPENAI_API_KEY=sk-...              ✅

# Optional (for better accuracy):
GOOGLE_CLOUD_STT_CREDENTIALS_PATH=  (not set)
```

---

## Performance

- 🎤 **Real-time speech:** Instant display (browser)
- 📤 **Upload/Stop Recording:** 2-5 sec after first load
- 🎯 **Accuracy:** 22.58% WER (very good)
- 💾 **Storage:** ~2.5GB model (downloads once)

---

## Next Steps

### Option A: Use NaijaVox (Now) ✅
1. Restart backend
2. Test in Multi-Chat
3. Done!

### Option B: Better Accuracy (Google Cloud)
1. Follow [IGBO_STT_SETUP.md](IGBO_STT_SETUP.md#option-2-google-cloud-speech-to-text-best-accuracy)
2. Takes 15 minutes
3. Slightly better accuracy

---

## Support

**Full guide:** [IGBO_STT_SETUP.md](IGBO_STT_SETUP.md)  
**Diagnostic:** `python test_igbo_stt.py`  
**Details:** [IGBO_STT_COMPLETE.md](IGBO_STT_COMPLETE.md)

---

**Status:** ✅ Ready to use  
**Last updated:** Sept 4, 2026
