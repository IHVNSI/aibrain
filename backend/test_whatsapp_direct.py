#!/usr/bin/env python
"""
Direct WhatsApp Service Test
Tests WhatsApp login without going through API
Useful for debugging Chrome startup issues
"""

import sys
import time
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.whatsapp_service import WhatsAppManager

def test_whatsapp_direct():
    print("\n" + "="*70)
    print("DIRECT WHATSAPP SERVICE TEST")
    print("="*70)
    
    try:
        print("\n[1] Getting WhatsApp instance...")
        wa = WhatsAppManager.get_instance("test_direct")
        print("✓ WhatsApp instance created")
        
        print("\n[2] Starting login (this will attempt to open Chrome)...")
        result = wa.start_login_async()
        
        print("\n[3] Login result:")
        print(f"    Success: {result.get('success')}")
        print(f"    Message: {result.get('message')}")
        print(f"    Logged In: {result.get('logged_in')}")
        print(f"    Has QR Code: {bool(result.get('qr_code'))}")
        
        if result.get('qr_code'):
            qr_len = len(result.get('qr_code', ''))
            print(f"    QR Code Size: {qr_len} bytes")
        
        if result.get('success'):
            print("\n✅ LOGIN SUCCESSFUL")
            if result.get('logged_in'):
                print("   Already logged in - connected!")
            else:
                print("   QR code ready for scanning")
                print("   Waiting for scan (max 120 seconds)...")
                
                # Wait for scan completion
                for i in range(120):
                    if wa.is_logged_in:
                        print(f"\n✅ SCAN DETECTED at {i}s")
                        print("   Successfully logged in via QR code!")
                        break
                    time.sleep(1)
                    if i % 10 == 0 and i > 0:
                        print(f"   Still waiting... ({i}s)")
        else:
            print("\n❌ LOGIN FAILED")
            print(f"   Error: {result.get('message')}")
        
        print("\n" + "="*70)
        return 0 if result.get('success') else 1
        
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test_whatsapp_direct())
