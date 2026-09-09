#!/usr/bin/env python
"""Test the complete diarization workflow."""

import requests
import json
import wave
import struct
import os

def create_valid_wav(filename, duration=3, sample_rate=16000):
    """Create a valid WAV file with multiple frequency tones (simulating different speakers)."""
    with wave.open(filename, 'w') as wav_file:
        n_channels = 1
        sample_width = 2
        framerate = sample_rate
        
        wav_file.setnchannels(n_channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(framerate)
        
        # Create audio with two different frequency bands (simulating two speakers)
        n_frames = int(duration * sample_rate)
        frames = []
        
        for i in range(n_frames):
            # First part: lower frequency (Speaker 1)
            if i < n_frames // 2:
                # 440 Hz sine wave (A4 note)
                value = int(32000 * 0.9 * (i * 440.0 * 2 * 3.14159 / sample_rate % 1.0) ** 0.5)
            # Second part: higher frequency (Speaker 2)
            else:
                # 880 Hz sine wave (A5 note)
                value = int(32000 * 0.9 * (i * 880.0 * 2 * 3.14159 / sample_rate % 1.0) ** 0.5)
            
            frames.append(struct.pack('<h', value))
        
        wav_file.writeframes(b''.join(frames))

# Login to get token
print("Logging in as admin...")
response = requests.post('http://127.0.0.1:5001/api/auth/login', 
    json={'email': 'admin@example.com', 'password': 'Brainer22'})

if response.status_code != 200:
    print(f"Login failed: {response.status_code}")
    exit(1)

token = response.json()['token']
print("✓ Login successful\n")

# Test with different languages
test_languages = ['english', 'igbo', 'hausa', 'yoruba']
headers = {'Authorization': f'Bearer {token}'}

for language in test_languages:
    # Create valid WAV file
    audio_path = f'/tmp/test_audio_{language}.wav'
    create_valid_wav(audio_path, duration=2)
    
    print(f"Testing diarization with {language.upper()} language...")
    
    with open(audio_path, 'rb') as f:
        files = {'audio': f}
        data = {'language': language}
        
        response = requests.post('http://127.0.0.1:5001/api/chat/multiperson-diarize', 
            headers=headers, files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        if result['success']:
            conversations = result['conversations']
            print(f"  ✓ Success! Detected {len(conversations)} speaker segment(s)")
            for conv in conversations:
                print(f"    - {conv['participant']}: {conv['translatedText'][:50]}...")
        else:
            print(f"  ✗ API Error: {result.get('error', 'Unknown error')}")
    else:
        print(f"  ✗ HTTP Error {response.status_code}")
    
    # Clean up
    try:
        os.remove(audio_path)
    except:
        pass
    
    print()

print("✓ All diarization tests completed!")
