#!/usr/bin/env python
"""Test multiple voice training uploads."""

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
print("✓ Logged in\n")

# Upload 3 voice samples
headers = {'Authorization': f'Bearer {token}'}
sample_texts = [
    "This is sample one for voice training",
    "Here is my second voice sample",
    "This is the third training sample"
]

for i, sample_text in enumerate(sample_texts, 1):
    print(f"Uploading voice sample {i}...")
    create_valid_wav(f'/tmp/voice_sample_{i}.wav', duration=2)
    
    with open(f'/tmp/voice_sample_{i}.wav', 'rb') as f:
        files = {'voice_sample': f}
        data = {'sample_text': sample_text}
        
        response = requests.post('http://127.0.0.1:5001/api/chat/train-user-voice', 
            headers=headers, files=files, data=data)
    
    result = response.json()
    if result['success']:
        print(f"  ✓ Sample {i} uploaded - Total samples: {result['samples_count']}")
    else:
        print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")

print("\n✓ Voice training test completed!")
