#!/usr/bin/env python3
"""
Test script to verify Igbo (and other Nigerian language) STT transcription.
Tests all available STT methods to identify which ones work.

Usage:
    python test_igbo_stt.py
"""

import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))

print("=" * 80)
print("IGBO SPEECH-TO-TEXT DIAGNOSTIC TEST")
print("=" * 80)

# Test 1: Check environment variables
print("\n[1] ENVIRONMENT CONFIGURATION")
print("-" * 80)

configs = {
    "Google Cloud STT": {
        "GOOGLE_CLOUD_STT_CREDENTIALS_PATH": os.getenv('GOOGLE_CLOUD_STT_CREDENTIALS_PATH'),
        "GOOGLE_APPLICATION_CREDENTIALS": os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
    },
    "OpenAI Whisper": {
        "OPENAI_API_KEY": "✓ Set" if os.getenv('OPENAI_API_KEY') else "✗ Not set",
    },
    "ElevenLabs": {
        "ELEVENLABS_API_KEY": "✓ Set" if os.getenv('ELEVENLABS_API_KEY') else "✗ Not set",
    },
    "NaijaVox-2.0": {
        "NAIJAVOX_DEVICE": os.getenv('NAIJAVOX_DEVICE', 'auto'),
        "NAIJAVOX_TORCH_DTYPE": os.getenv('NAIJAVOX_TORCH_DTYPE', 'float16'),
    }
}

for service, config in configs.items():
    print(f"\n{service}:")
    for key, value in config.items():
        status = "✓" if value else "✗"
        display_value = value if isinstance(value, str) and len(str(value)) < 50 else ("Set" if value else "Not set")
        print(f"  {status} {key}: {display_value}")

# Test 2: Check Python packages
print("\n[2] CHECKING DEPENDENCIES")
print("-" * 80)

packages = {
    "google-cloud-speech": "google.cloud.speech_v1",
    "openai": "openai",
    "transformers": "transformers",
    "torch": "torch",
    "librosa": "librosa",
    "torchaudio": "torchaudio",
    "elevenlabs": "elevenlabs",
}

for package_name, import_name in packages.items():
    try:
        module = __import__(import_name)
        version = getattr(module, '__version__', 'unknown')
        print(f"✓ {package_name}: {version}")
    except ImportError:
        print(f"✗ {package_name}: NOT INSTALLED")

# Test 3: Test STT functions
print("\n[3] TESTING STT FUNCTIONS")
print("-" * 80)

# Create a simple test audio file (silence/tone for testing)
import io
try:
    import wave
    
    # Create a test WAV file with 1 second of silence
    test_audio_path = "/tmp/test_igbo.wav"
    
    # Generate test audio
    sample_rate = 16000
    duration = 2  # seconds
    
    import array
    audio_data = array.array('h', [0] * (sample_rate * duration))
    
    with wave.open(test_audio_path, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    print(f"✓ Created test audio file: {test_audio_path}")
    
    # Test each STT method
    from backend.app.api.multiperson_chat import (
        _transcribe_with_google_cloud,
        _transcribe_with_whisper,
        _transcribe_with_naijavox,
        _transcribe_with_elevenlabs,
    )
    
    test_cases = [
        ("Google Cloud (ig-NG)", lambda: _transcribe_with_google_cloud(test_audio_path, 'ig-NG', 'igbo')),
        ("Google Cloud (yo-NG)", lambda: _transcribe_with_google_cloud(test_audio_path, 'yo-NG', 'yoruba')),
        ("Google Cloud (ha-NG)", lambda: _transcribe_with_google_cloud(test_audio_path, 'ha-NG', 'hausa')),
        ("Whisper (ig)", lambda: _transcribe_with_whisper(test_audio_path, 'ig', 'igbo')),
        ("Whisper (yo)", lambda: _transcribe_with_whisper(test_audio_path, 'yo', 'yoruba')),
        ("NaijaVox (igbo)", lambda: _transcribe_with_naijavox(test_audio_path, 'igbo', 'Igbo')),
        ("NaijaVox (yoruba)", lambda: _transcribe_with_naijavox(test_audio_path, 'yoruba', 'Yoruba')),
        ("ElevenLabs", lambda: _transcribe_with_elevenlabs(test_audio_path, 'ig', 'igbo')),
    ]
    
    for test_name, test_func in test_cases:
        try:
            print(f"\n  Testing {test_name}...")
            result = test_func()
            if result:
                print(f"    ✓ Success: {result[:100]}...")
            else:
                print(f"    ⚠ No transcript returned (may be normal for silence)")
        except Exception as e:
            print(f"    ✗ Error: {str(e)[:200]}")
    
    # Clean up
    try:
        os.remove(test_audio_path)
    except:
        pass
        
except Exception as e:
    print(f"✗ Error creating test audio: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Check Language Code Mappings
print("\n[4] LANGUAGE CODE MAPPINGS")
print("-" * 80)

from backend.app.api.multiperson_chat import perform_speech_to_text

language_map = {
    'english': {'google': 'en-US', 'whisper': 'en', 'naijavox': 'nigerian_english'},
    'igbo': {'google': 'ig-NG', 'whisper': 'ig', 'naijavox': 'igbo'},
    'hausa': {'google': 'ha-NG', 'whisper': 'ha', 'naijavox': 'hausa'},
    'yoruba': {'google': 'yo-NG', 'whisper': 'yo', 'naijavox': 'yoruba'},
    'pidgin': {'google': 'en-US', 'whisper': 'en', 'naijavox': 'pidgin'},
}

for language, codes in language_map.items():
    print(f"\n{language.upper()}:")
    for service, code in codes.items():
        print(f"  {service}: {code}")

# Test 5: Web Speech API Language Codes
print("\n[5] WEB SPEECH API LANGUAGE CODES (Frontend)")
print("-" * 80)

web_speech_codes = {
    'english': 'en-US',
    'igbo': 'ig-NG',
    'hausa': 'ha-NG',
    'yoruba': 'yo-NG'
}

for language, code in web_speech_codes.items():
    print(f"  {language}: {code} ✓")

print("\nNote: Web Speech API uses BCP 47 language tags.")
print("Igbo (ig-NG), Yoruba (yo-NG), Hausa (ha-NG) are Nigerian variants.")

# Summary
print("\n" + "=" * 80)
print("DIAGNOSTIC SUMMARY")
print("=" * 80)

recommendations = []

if not (os.getenv('GOOGLE_CLOUD_STT_CREDENTIALS_PATH') or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')):
    recommendations.append(
        "❌ Google Cloud STT credentials not found.\n"
        "   Action: Set GOOGLE_CLOUD_STT_CREDENTIALS_PATH in .env with path to JSON key file"
    )
else:
    recommendations.append("✓ Google Cloud STT is configured")

if not os.getenv('OPENAI_API_KEY'):
    recommendations.append(
        "❌ OpenAI API key not found (needed as fallback).\n"
        "   Action: Set OPENAI_API_KEY in .env"
    )
else:
    recommendations.append("✓ OpenAI Whisper fallback is configured")

# Check if NaijaVox dependencies are installed
try:
    import torch
    import librosa
    recommendations.append("✓ NaijaVox dependencies (torch, librosa) are installed")
except ImportError:
    recommendations.append(
        "❌ NaijaVox dependencies missing.\n"
        "   Action: Run: pip install torch torchaudio librosa"
    )

print("\nRECOMMENDATIONS:")
print("-" * 80)
for i, rec in enumerate(recommendations, 1):
    print(f"{i}. {rec}\n")

print("\nQUICK START SETUP FOR IGBO STT:")
print("-" * 80)
print("""
OPTION 1: Google Cloud (RECOMMENDED - Best for African languages)
1. Create Google Cloud project: https://console.cloud.google.com
2. Enable Speech-to-Text API
3. Create service account with speech.googleapis.com permission
4. Download JSON key file
5. Set in .env: GOOGLE_CLOUD_STT_CREDENTIALS_PATH=/path/to/key.json

OPTION 2: NaijaVox-2.0 (FREE - Offline, optimized for Nigerian languages)
1. Already installed via requirements.txt
2. Model (~2.5GB) will auto-download on first use
3. Supports: Igbo, Yoruba, Hausa, Nigerian Pidgin
4. Set in .env: NAIJAVOX_DEVICE=cuda (or cpu if no GPU)

OPTION 3: OpenAI Whisper (Fallback)
1. Already configured with OPENAI_API_KEY
2. Supports Igbo but with less accuracy than Google Cloud

For real-time Web Speech API transcription:
- Browser must support Web Speech API (Chrome, Edge, Safari)
- Language codes are automatically mapped (igbo → ig-NG, etc.)
- Works client-side, no backend needed for interim results
""")

print("\nNEXT STEPS:")
print("-" * 80)
print("""
1. Choose your preferred STT method (Google Cloud recommended)
2. Update .env with necessary credentials
3. Restart the backend: python run.py
4. Go to Multi-Chat tab in the app
5. Select language: Igbo, Yoruba, or Hausa
6. Click "Start Recording" or "Upload Audio File"
7. Verify real-time transcription appears in the correct language
""")
