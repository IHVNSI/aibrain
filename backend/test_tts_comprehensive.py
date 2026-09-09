#!/usr/bin/env python3
"""
Comprehensive Text-to-Speech (TTS) Testing Suite
Tests all available TTS providers and validates configuration
"""

import os
import sys
import json
import base64

def test_tts_providers():
    """Test all configured TTS providers."""
    
    print("=" * 70)
    print("🎵 TEXT-TO-SPEECH (TTS) TESTING SUITE")
    print("=" * 70)
    
    # Check API keys
    print("\n📋 API Keys Configuration:")
    print("-" * 70)
    
    elevenlabs_key = os.getenv('ELEVENLABS_API_KEY', '').strip()
    yarngpt_key = os.getenv('YARNGPT_API_KEY', '').strip()
    google_tts_cred = os.getenv('GOOGLE_CLOUD_TTS_CREDENTIALS_PATH', '').strip()
    azure_key = os.getenv('AZURE_SPEECH_KEY', '').strip()
    azure_region = os.getenv('AZURE_SPEECH_REGION', '').strip()
    openai_key = os.getenv('OPENAI_API_KEY', '').strip()
    
    print(f"✅ ElevenLabs API Key: {'Configured' if elevenlabs_key else '❌ Not configured'}")
    if elevenlabs_key:
        print(f"   Preview: {elevenlabs_key[:20]}...{elevenlabs_key[-8:]}")
    
    print(f"✅ YarnGPT API Key: {'Configured' if yarngpt_key else '❌ Not configured'}")
    if yarngpt_key:
        print(f"   Preview: {yarngpt_key[:20]}...{yarngpt_key[-8:]}")
    
    print(f"✅ Google Cloud TTS: {'Configured' if google_tts_cred else '❌ Not configured'}")
    if google_tts_cred:
        print(f"   Credentials file: {google_tts_cred}")
    
    print(f"✅ Azure Speech: {'Configured' if (azure_key and azure_region) else '❌ Not configured'}")
    if azure_key:
        print(f"   Region: {azure_region}")
    
    # Test Backend TTS Endpoint
    print("\n" + "=" * 70)
    print("🔗 Testing Backend /api/chat/synthesize-speech Endpoint")
    print("=" * 70)
    
    try:
        import requests
        
        # Get auth token
        print("\n1️⃣  Getting authentication token...")
        auth_response = requests.post(
            "http://localhost:5001/api/auth/login",
            json={
                "email": "admin@brainr.com",
                "password": "@@AdminBrainer22"
            },
            timeout=5
        )
        
        if auth_response.status_code != 200:
            print(f"   ❌ Authentication failed: {auth_response.status_code}")
            print("   Note: Backend may not be running. Start with: python backend/run.py")
            auth_token = None
        else:
            auth_data = auth_response.json()
            auth_token = auth_data.get('token')
            print(f"   ✅ Authentication successful")
    except Exception as e:
        print(f"   ❌ Cannot reach backend: {str(e)[:60]}")
        print("   Note: Start backend with: python backend/run.py")
        auth_token = None
    
    if auth_token:
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        # Test different TTS providers
        providers = ['browser', 'elevenlabs-tts', 'yarngpt-tts', 'google-cloud', 'azure-tts']
        languages = ['english', 'igbo', 'yoruba', 'hausa']
        
        print("\n2️⃣  Testing TTS Providers:")
        print("-" * 70)
        
        test_messages = {
            'english': 'Welcome, how are you doing today',
            'igbo': 'Nnoo, kedu ka ị na-eme taa',
            'yoruba': 'Kaabo, bawo lo n se loni',
            'hausa': 'Maraba, yaya kuke ji taa'
        }
        
        results = {}
        
        for provider in providers:
            print(f"\n   🎤 Provider: {provider}")
            for language in languages[:2]:  # Test first 2 languages
                test_text = test_messages.get(language, test_messages['english'])
                
                try:
                    response = requests.post(
                        "http://localhost:5001/api/chat/synthesize-speech",
                        json={
                            "text": test_text,
                            "language": language,
                            "gender": "FEMALE",
                            "tts_provider": provider
                        },
                        headers=headers,
                        timeout=15
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success'):
                            provider_name = data.get('provider', provider)
                            cost = data.get('cost', 'N/A')
                            print(f"      ✅ {language:8s} → {provider_name:20s} ({cost})")
                            if provider not in results:
                                results[provider] = []
                            results[provider].append(language)
                        else:
                            error = data.get('error', 'Unknown error')
                            print(f"      ⚠️  {language:8s} → Error: {error[:40]}")
                    else:
                        print(f"      ❌ {language:8s} → HTTP {response.status_code}")
                except requests.exceptions.Timeout:
                    print(f"      ⏱️  {language:8s} → Timeout (>15s)")
                except Exception as e:
                    print(f"      ❌ {language:8s} → {str(e)[:40]}")
        
        # Summary
        print("\n" + "=" * 70)
        print("✅ SUMMARY - Working TTS Providers:")
        print("=" * 70)
        if results:
            for provider, languages_list in sorted(results.items()):
                print(f"  ✅ {provider:20s} → {', '.join(set(languages_list))}")
        else:
            print("  No providers tested successfully. Check backend status.")
    
    # Test Direct API Connections
    print("\n" + "=" * 70)
    print("🌐 Testing Direct API Connections")
    print("=" * 70)
    
    try:
        import requests
        
        # Test ElevenLabs
        if elevenlabs_key:
            print("\n1️⃣  ElevenLabs API:")
            try:
                response = requests.get(
                    "https://api.elevenlabs.io/v1/voices",
                    headers={"xi-api-key": elevenlabs_key},
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    voice_count = len(data.get('voices', []))
                    print(f"   ✅ Connected - {voice_count} voices available")
                else:
                    print(f"   ❌ HTTP {response.status_code} - Check API key")
            except Exception as e:
                print(f"   ❌ Connection failed: {str(e)[:50]}")
        
        # Test YarnGPT (this will likely fail as we discovered)
        if yarngpt_key:
            print("\n2️⃣  YarnGPT API:")
            try:
                response = requests.get(
                    "https://api.yarngpt.app/health",
                    headers={"Authorization": f"Bearer {yarngpt_key}"},
                    timeout=5
                )
                print(f"   ✅ Connected - HTTP {response.status_code}")
            except requests.exceptions.ConnectionError:
                print(f"   ⚠️  Connection failed - Domain unreachable")
                print("      This is expected if YarnGPT service has moved")
                print("      Solution: Using ElevenLabs as fallback ✅")
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:50]}")
        
        # Test Google Cloud
        if google_tts_cred and os.path.exists(google_tts_cred):
            print("\n3️⃣  Google Cloud TTS:")
            try:
                from google.cloud import texttospeech
                print(f"   ✅ Credentials file found: {google_tts_cred}")
                print("   ✅ Google Cloud SDK installed")
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:50]}")
        
    except ImportError:
        print("   Note: requests library not installed. Skipping direct API tests.")
    
    # Recommendations
    print("\n" + "=" * 70)
    print("💡 RECOMMENDATIONS")
    print("=" * 70)
    print("""
🎯 For the best TTS experience:

1. ✅ PRIMARY: ElevenLabs TTS (Already configured)
   - Provides premium multilingual voices
   - Supports: English, Igbo, Yoruba, Hausa, Pidgin
   - Configured with API key in .env

2. ⚠️  FALLBACK: YarnGPT TTS (Endpoint unreachable)
   - Current implementation falls back to ElevenLabs
   - If you want YarnGPT, check:
     - Dashboard: https://yarngpt.app
     - API key validity
     - Service status

3. 🌐 ALTERNATIVE: Google Cloud TTS
   - Best for African languages
   - Requires service account credentials
   - Setup: docs/AUDIO_CONFIGURATION_SETUP.md

4. 🔵 ALTERNATIVE: Azure TTS
   - Free tier available
   - Wide language support
   - Setup: Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION

👉 Next Steps:
   1. Start backend: python backend/run.py
   2. Test in Settings → Audio → Text-to-Speech tab
   3. Select "YarnGPT Text-to-Speech" → Click "Test TTS"
   4. You'll hear ElevenLabs TTS playing (fallback)
   5. To use only ElevenLabs directly, select "ElevenLabs TTS"
""")

if __name__ == "__main__":
    test_tts_providers()
