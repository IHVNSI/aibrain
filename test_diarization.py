#!/usr/bin/env python
"""Test the diarization endpoint."""

import requests
import json
import os

# Login to get token
print("Logging in...")
response = requests.post('http://127.0.0.1:5001/api/auth/login', 
    json={'email': 'admin@example.com', 'password': 'Brainer22'})

if response.status_code != 200:
    print(f"Login failed: {response.status_code}")
    print(response.text)
    exit(1)

token = response.json()['token']
print("✓ Login successful")

# Create a test audio file
audio_path = '/tmp/test_audio.wav'
with open(audio_path, 'wb') as f:
    f.write(b'RIFF\x00\x00\x00\x00WAVE')

print(f"Created test audio file at {audio_path}")

# Test diarization endpoint
headers = {'Authorization': f'Bearer {token}'}
with open(audio_path, 'rb') as f:
    files = {'audio': f}
    data = {'language': 'english'}
    
    print("\nTesting diarization endpoint...")
    response = requests.post('http://127.0.0.1:5001/api/chat/multiperson-diarize', 
        headers=headers, files=files, data=data)

print(f"Status Code: {response.status_code}")
print(f"\nResponse:")
print(json.dumps(response.json(), indent=2))

# Clean up
try:
    os.remove(audio_path)
    print(f"\n✓ Cleaned up test file")
except:
    pass
