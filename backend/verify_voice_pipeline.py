"""Verify all multilingual voice pipeline imports and configuration."""
import sys
import os

print("=" * 60)
print("🔍 MULTILINGUAL VOICE PIPELINE - IMPORT VERIFICATION")
print("=" * 60)

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

errors = []
warnings = []

# Test 1: Core translation module
print("\n✓ Testing: app.translation module")
try:
    from app.translation import translate, translate_to_english, LANGUAGE_CODES, LANGUAGE_NAMES
    print("  ✅ Translation module imported successfully")
    print(f"     - Supported languages: {list(LANGUAGE_CODES.keys())}")
    print(f"     - Functions: translate, translate_to_english, translate_with_google_cloud, translate_with_llm")
except Exception as e:
    errors.append(f"Translation module import failed: {e}")
    print(f"  ❌ FAILED: {e}")

# Test 2: Multilingual voice pipeline
print("\n✓ Testing: app.multilingual_voice_pipeline module")
try:
    from app.multilingual_voice_pipeline import (
        process_multilingual_voice,
        transcribe_audio,
        translate_to_english,
        translate_from_english,
        synthesize_speech,
        LANGUAGE_CONFIGS
    )
    print("  ✅ Multilingual pipeline module imported successfully")
    print(f"     - Supported languages: {list(LANGUAGE_CONFIGS.keys())}")
    print(f"     - Functions: process_multilingual_voice, transcribe_audio, synthesize_speech")
except Exception as e:
    errors.append(f"Multilingual pipeline module import failed: {e}")
    print(f"  ❌ FAILED: {e}")

# Test 3: Voice API blueprint
print("\n✓ Testing: app.api.voice module")
try:
    from app.api.voice import voice_bp, process_voice, test_transcription, test_translation, test_tts
    print("  ✅ Voice API blueprint imported successfully")
    print(f"     - Blueprint name: {voice_bp.name}")
    print(f"     - Blueprint URL prefix: {voice_bp.url_prefix}")
    print(f"     - Endpoints: process, test-transcription, test-translation, test-tts, languages")
except Exception as e:
    errors.append(f"Voice API blueprint import failed: {e}")
    print(f"  ❌ FAILED: {e}")

# Test 4: Google Cloud libraries
print("\n✓ Testing: Google Cloud libraries")
try:
    from google.cloud import texttospeech
    print("  ✅ google-cloud-texttospeech installed")
except ImportError as e:
    warnings.append(f"google-cloud-texttospeech not installed (optional): {e}")
    print(f"  ⚠️  google-cloud-texttospeech not installed (optional)")

try:
    from google.cloud import translate_v2
    print("  ✅ google-cloud-translate installed")
except ImportError as e:
    warnings.append(f"google-cloud-translate not installed (optional): {e}")
    print(f"  ⚠️  google-cloud-translate not installed (optional)")

try:
    from google.cloud import speech_v1
    print("  ✅ google-cloud-speech installed")
except ImportError as e:
    warnings.append(f"google-cloud-speech not installed (optional): {e}")
    print(f"  ⚠️  google-cloud-speech not installed (optional)")

# Test 5: Audio libraries
print("\n✓ Testing: Audio processing libraries")
try:
    import librosa
    print("  ✅ librosa installed")
except ImportError as e:
    errors.append(f"librosa not installed (required): {e}")
    print(f"  ❌ librosa not installed (required for NaijaVox)")

try:
    import torch
    print("  ✅ torch installed")
except ImportError as e:
    errors.append(f"torch not installed (required): {e}")
    print(f"  ❌ torch not installed (required for NaijaVox)")

try:
    import torchaudio
    print("  ✅ torchaudio installed")
except ImportError as e:
    errors.append(f"torchaudio not installed (required): {e}")
    print(f"  ❌ torchaudio not installed (required for NaijaVox)")

try:
    from transformers import WhisperForConditionalGeneration
    print("  ✅ transformers installed")
except ImportError as e:
    errors.append(f"transformers not installed (required): {e}")
    print(f"  ❌ transformers not installed (required for NaijaVox)")

try:
    import pydub
    print("  ✅ pydub installed")
except ImportError as e:
    warnings.append(f"pydub not installed (optional): {e}")
    print(f"  ⚠️  pydub not installed (optional)")

# Test 6: Configuration check
print("\n✓ Testing: Configuration (.env)")
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    google_stt = os.getenv('GOOGLE_CLOUD_STT_CREDENTIALS_PATH', 'NOT SET')
    google_tts = os.getenv('GOOGLE_CLOUD_TTS_CREDENTIALS_PATH', 'NOT SET')
    google_trans = os.getenv('GOOGLE_CLOUD_TRANSLATION_CREDENTIALS_PATH', 'NOT SET')
    
    print(f"  - GOOGLE_CLOUD_STT_CREDENTIALS_PATH: {google_stt}")
    print(f"  - GOOGLE_CLOUD_TTS_CREDENTIALS_PATH: {google_tts}")
    print(f"  - GOOGLE_CLOUD_TRANSLATION_CREDENTIALS_PATH: {google_trans}")
    
    if google_stt == 'NOT SET' or google_tts == 'NOT SET' or google_trans == 'NOT SET':
        warnings.append("Google Cloud credentials not configured in .env (optional for now)")
        print("  ⚠️  Google Cloud credentials not configured")
    else:
        print("  ✅ Google Cloud credentials configured")
except Exception as e:
    warnings.append(f"Configuration check failed: {e}")
    print(f"  ⚠️  Configuration check failed: {e}")

# Summary
print("\n" + "=" * 60)
print("📋 VERIFICATION SUMMARY")
print("=" * 60)

if errors:
    print(f"\n❌ ERRORS ({len(errors)}):")
    for i, error in enumerate(errors, 1):
        print(f"   {i}. {error}")
else:
    print("\n✅ No critical errors!")

if warnings:
    print(f"\n⚠️  WARNINGS ({len(warnings)}):")
    for i, warning in enumerate(warnings, 1):
        print(f"   {i}. {warning}")
else:
    print("\n✅ No warnings!")

print("\n" + "=" * 60)

if errors:
    print("❌ VERIFICATION FAILED - Please fix errors above")
    sys.exit(1)
else:
    print("✅ VERIFICATION SUCCESSFUL - Ready for testing!")
    print("\nNext steps:")
    print("1. Configure Google Cloud credentials in .env")
    print("2. Start backend: python run.py")
    print("3. Test API endpoints in MULTILINGUAL_VOICE_PIPELINE.md")
    sys.exit(0)
