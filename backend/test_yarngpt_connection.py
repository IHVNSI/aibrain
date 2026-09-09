#!/usr/bin/env python3
"""Test YarnGPT TTS API connection and endpoints."""

import os
import requests
import json

# Get API key from environment
yarngpt_key = os.getenv('YARNGPT_API_KEY', 'sk_live_-JsXY4bLc2TK-GAGf_-JNXAXolH0xxGEzr3HYx6mL_Y').strip()

print("=" * 60)
print("YarnGPT API Connection Test")
print("=" * 60)
print(f"\nAPI Key configured: {bool(yarngpt_key)}")
if yarngpt_key:
    print(f"Key preview: {yarngpt_key[:20]}...{yarngpt_key[-8:]}\n")

headers = {
    "Authorization": f"Bearer {yarngpt_key}",
    "Content-Type": "application/json"
}

# Test different endpoints
endpoints = [
    "https://api.yarngpt.app/health",
    "https://api.yarngpt.app/v1/health",
    "https://api.yarngpt.app/v1/tts",
    "https://yarngpt.app/api/v1/tts",
    "https://yarngpt.app/health"
]

for endpoint in endpoints:
    print(f"\n1️⃣  Testing: {endpoint}")
    try:
        response = requests.get(endpoint if endpoint.endswith('/health') else endpoint, 
                              headers=headers, 
                              timeout=5,
                              json={"test": True} if not endpoint.endswith('/health') else None)
        print(f"   Status: {response.status_code}")
        print(f"   Response headers: {dict(response.headers)}")
        if response.text:
            try:
                print(f"   Response body: {response.json()}")
            except:
                print(f"   Response body: {response.text[:200]}")
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ Connection Error: {str(e)[:80]}")
    except requests.exceptions.Timeout:
        print(f"   ❌ Timeout")
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:80]}")

# Test TTS endpoint with actual request
print("\n" + "=" * 60)
print("2️⃣  Testing TTS Synthesis")
print("=" * 60)

test_payload = {
    "text": "Hello, this is a test",
    "language": "english",
    "voice_type": "premium",
    "gender": "FEMALE"
}

print(f"\nPayload: {json.dumps(test_payload, indent=2)}")

try:
    print(f"\n🔗 POST https://api.yarngpt.app/v1/tts")
    response = requests.post("https://api.yarngpt.app/v1/tts",
                            json=test_payload,
                            headers=headers,
                            timeout=10)
    print(f"   Status: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")
    if response.status_code == 200:
        print(f"   ✅ Success! Audio data received: {len(response.content)} bytes")
    else:
        try:
            print(f"   Response: {response.json()}")
        except:
            print(f"   Response: {response.text[:300]}")
except requests.exceptions.ConnectionError as e:
    print(f"   ❌ Connection Error: No internet or endpoint unreachable")
    print(f"   Details: {str(e)[:100]}")
except requests.exceptions.Timeout:
    print(f"   ❌ Timeout: API not responding")
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

print("\n" + "=" * 60)
print("Troubleshooting:")
print("=" * 60)
print("""
If YarnGPT API is unreachable:

1. Check internet connection:
   - Ping google.com
   - Check if DNS resolution works

2. Verify API endpoint:
   - Visit https://yarngpt.app in a browser
   - Check if service status page shows operational

3. Verify API key:
   - Log in to https://yarngpt.app/dashboard
   - Check if API key is valid and not revoked
   - Check if account has credits/subscription

4. Check firewall/proxy:
   - May be blocking external API calls
   - Check if corporate firewall blocks api.yarngpt.app

5. Alternative TTS services:
   - Google Cloud TTS (requires credentials file)
   - ElevenLabs TTS (already configured)
   - Azure Text-to-Speech
""")
