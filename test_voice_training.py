#!/usr/bin/env python
"""Test the voice training endpoint."""

import requests
import wave
import struct
import json

def create_valid_wav(filename, duration=2):
    """Create a valid WAV file."""
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        
        frames = [struct.pack('<h', 0)] * (16000 * duration)
        wav_file.writeframes(b''.join(frames))

# Login
print("Logging in...")
response = requests.post('http://127.0.0.1:5001/api/auth/login', 
    json={'email': 'admin@example.com', 'password': 'Brainer22'})
token = response.json()['token']
print("✓ Logged in")

# Create test audio
print("\nCreating test voice sample...")
create_valid_wav('/tmp/voice_sample.wav', duration=3)
print("✓ Voice sample created")

# Test voice training endpoint
print("\nTesting voice training endpoint...")
headers = {'Authorization': f'Bearer {token}'}

with open('/tmp/voice_sample.wav', 'rb') as f:
    files = {'voice_sample': f}
    data = {'sample_text': 'This is my voice sample for authentication'}
    
    response = requests.post('http://127.0.0.1:5001/api/chat/train-user-voice', 
        headers=headers, files=files, data=data)

print(f"Status: {response.status_code}")
result = response.json()
print(json.dumps(result, indent=2))

if result['success']:
    print("\n✓ Voice training successful!")
    print(f"  Total training samples for user: {result['samples_count']}")
else:
    print(f"\n✗ Error: {result.get('error', 'Unknown error')}")
