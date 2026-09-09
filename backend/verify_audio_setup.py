#!/usr/bin/env python
"""Verify ElevenLabs Scribe and YarnGPT setup."""

import os
from dotenv import load_dotenv

load_dotenv()

print("\n=== AUDIO SERVICES SETUP VERIFICATION ===\n")

# Check API Keys
elevenlabs_key = os.getenv('ELEVENLABS_API_KEY', '').strip()
yarngpt_key = os.getenv('YARNGPT_API_KEY', '').strip()

print(f"✓ ELEVENLABS_API_KEY set: {bool(elevenlabs_key)}")
if elevenlabs_key:
    print(f"  Key preview: {elevenlabs_key[:15]}...{elevenlabs_key[-8:]}")

print(f"✓ YARNGPT_API_KEY set: {bool(yarngpt_key)}")
if yarngpt_key:
    print(f"  Key preview: {yarngpt_key[:15]}...{yarngpt_key[-8:]}")

# Check SDK imports
print("\n=== INSTALLED DEPENDENCIES ===\n")

deps_ok = True

try:
    from elevenlabs import ElevenLabs
    print("✓ ElevenLabs SDK: INSTALLED")
except ImportError as e:
    print(f"✗ ElevenLabs SDK: MISSING - {e}")
    deps_ok = False

try:
    import requests
    print("✓ requests library: INSTALLED")
except ImportError as e:
    print(f"✗ requests library: MISSING - {e}")
    deps_ok = False

try:
    import azure.cognitiveservices.speech as speechsdk
    print("✓ Azure Speech SDK: INSTALLED")
except ImportError:
    print("⚠ Azure Speech SDK: NOT INSTALLED (optional)")

# Test ElevenLabs connectivity
print("\n=== API CONNECTIVITY ===\n")

if elevenlabs_key:
    try:
        from elevenlabs import ElevenLabs
        client = ElevenLabs(api_key=elevenlabs_key)
        voices = client.voices.get_all()
        print(f"✓ ElevenLabs API: CONNECTED ({len(voices) if voices else 0} voices available)")
    except Exception as e:
        print(f"✗ ElevenLabs API: ERROR - {str(e)[:60]}")
else:
    print("⚠ ElevenLabs API: SKIPPED (no API key)")

if yarngpt_key:
    try:
        import requests
        headers = {"Authorization": f"Bearer {yarngpt_key}"}
        resp = requests.get("https://api.yarngpt.app/health", headers=headers, timeout=5)
        print(f"✓ YarnGPT API: CONNECTED (HTTP {resp.status_code})")
    except requests.exceptions.ConnectionError:
        print("⚠ YarnGPT API: NO INTERNET (endpoint unreachable)")
    except Exception as e:
        print(f"✗ YarnGPT API: ERROR - {str(e)[:60]}")
else:
    print("⚠ YarnGPT API: SKIPPED (no API key)")

# Summary
print("\n=== SUMMARY ===\n")
if elevenlabs_key and yarngpt_key and deps_ok:
    print("✓ All audio services configured and ready!")
    print("\n  Available:")
    print("  - ElevenLabs Scribe API (STT with diarization)")
    print("  - YarnGPT Text-to-Speech")
else:
    print("⚠ Some services may not be fully configured")
    if not elevenlabs_key:
        print("  Missing: ELEVENLABS_API_KEY")
    if not yarngpt_key:
        print("  Missing: YARNGPT_API_KEY")
    if not deps_ok:
        print("  Missing: Required Python dependencies")

print("\n")
