#!/usr/bin/env python
"""Debug the English language diarization error."""

import requests
import wave
import struct
import traceback

def create_valid_wav(filename):
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        
        frames = [struct.pack('<h', 0)] * 32000
        wav_file.writeframes(b''.join(frames))

try:
    # Login
    print("Logging in...")
    response = requests.post('http://127.0.0.1:5001/api/auth/login', 
        json={'email': 'admin@example.com', 'password': 'Brainer22'})
    token = response.json()['token']
    print("✓ Logged in")
    
    # Create and upload
    print("Creating test audio file...")
    create_valid_wav('/tmp/test_english.wav')
    headers = {'Authorization': f'Bearer {token}'}
    
    print("Testing diarization with English...")
    with open('/tmp/test_english.wav', 'rb') as f:
        response = requests.post('http://127.0.0.1:5001/api/chat/multiperson-diarize', 
            headers=headers, files={'audio': f}, data={'language': 'english'})
    
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Error Response:")
        print(response.text[:1000])
    else:
        print("✓ Success!")
        import json
        print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Exception: {e}")
    traceback.print_exc()
