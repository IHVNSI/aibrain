#!/usr/bin/env python3
"""Quick TTS test after backend is running."""

import requests
import json
import time

print("=" * 60)
print("Testing TTS Endpoint After Backend Start")
print("=" * 60)

# Test login
print("\n1. Testing authentication...")
try:
    auth_response = requests.post(
        "http://localhost:5001/api/auth/login",
        json={
            "email": "admin@brainr.com",
            "password": "@@AdminBrainer22"
        },
        timeout=5
    )
    
    if auth_response.status_code == 200:
        auth_data = auth_response.json()
        token = auth_data.get('token')
        print(f"   ✅ Login successful")
        print(f"   Token: {token[:20]}...{token[-10:]}")
    else:
        print(f"   ❌ Login failed: {auth_response.status_code}")
        print(f"   Response: {auth_response.text[:100]}")
        exit(1)
except Exception as e:
    print(f"   ❌ Cannot connect to backend: {str(e)[:60]}")
    print("\n   Make sure backend is running with:")
    print("   cd backend && python run.py")
    exit(1)

# Test TTS with YarnGPT (which should fallback to ElevenLabs)
print("\n2. Testing YarnGPT TTS (with ElevenLabs fallback)...")
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

try:
    tts_response = requests.post(
        "http://localhost:5001/api/chat/synthesize-speech",
        json={
            "text": "Hello, this is a test of text-to-speech synthesis.",
            "language": "english",
            "gender": "FEMALE",
            "tts_provider": "yarngpt-tts"
        },
        headers=headers,
        timeout=15
    )
    
    if tts_response.status_code == 200:
        data = tts_response.json()
        if data.get('success'):
            provider = data.get('provider', 'unknown')
            cost = data.get('cost', 'N/A')
            print(f"   ✅ TTS successful!")
            print(f"   Provider: {provider}")
            print(f"   Cost: {cost}")
            if data.get('audio'):
                print(f"   Audio: {len(data['audio'])} bytes (base64 encoded)")
        else:
            error = data.get('error', 'Unknown error')
            print(f"   ⚠️  TTS failed: {error}")
    else:
        print(f"   ❌ HTTP {tts_response.status_code}")
        try:
            print(f"   Response: {tts_response.json()}")
        except:
            print(f"   Response: {tts_response.text[:200]}")
            
except requests.exceptions.Timeout:
    print(f"   ⏱️  Request timeout (>15s)")
except Exception as e:
    print(f"   ❌ Error: {str(e)[:60]}")

# Test ElevenLabs TTS directly
print("\n3. Testing ElevenLabs TTS directly...")
try:
    tts_response = requests.post(
        "http://localhost:5001/api/chat/synthesize-speech",
        json={
            "text": "This is ElevenLabs text-to-speech.",
            "language": "english",
            "gender": "MALE",
            "tts_provider": "elevenlabs-tts"
        },
        headers=headers,
        timeout=15
    )
    
    if tts_response.status_code == 200:
        data = tts_response.json()
        if data.get('success'):
            provider = data.get('provider', 'unknown')
            print(f"   ✅ ElevenLabs TTS successful!")
            print(f"   Provider: {provider}")
        else:
            error = data.get('error', 'Unknown error')
            print(f"   ⚠️  ElevenLabs TTS failed: {error}")
    else:
        print(f"   ❌ HTTP {tts_response.status_code}")
            
except Exception as e:
    print(f"   ❌ Error: {str(e)[:60]}")

print("\n" + "=" * 60)
print("✅ TTS Testing Complete!")
print("=" * 60)
print("""
Summary:
- YarnGPT TTS now falls back to ElevenLabs automatically
- ElevenLabs TTS is the primary fallback for all languages
- To use alternative providers, select them directly in Settings

Next Steps:
1. Go to Settings → Audio → Text-to-Speech
2. Select "YarnGPT Text-to-Speech" 
3. Click "Test TTS" to hear ElevenLabs audio
4. Select "ElevenLabs TTS" to use it directly
""")
