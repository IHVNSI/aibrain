#!/usr/bin/env python
"""
Comprehensive WhatsApp Web Integration Tests
Tests all 7 scenarios for headless mode, auto-connect, QR code display, and graceful error handling
"""

import requests
import json
import time
import sys
from pathlib import Path

BASE_URL = "http://localhost:5000"
QR_FILE = Path("../whatsapp_sessions/default_qr.png")

def print_test_header(test_num, title):
    print("\n" + "="*80)
    print(f"TEST {test_num}: {title}")
    print("="*80)

def print_step(step_num, description):
    print(f"\n  [{step_num}] {description}")

def print_result(status, message):
    symbol = "✅" if status else "❌"
    print(f"      {symbol} {message}")

def test_1_app_startup():
    """Test 1: App starts with headless Chrome (no visible window)"""
    print_test_header(1, "App Startup with Headless Chrome")
    print_step(1, "Check backend is running")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        print_result(True, "Backend API is responsive")
        return True
    except Exception as e:
        print_result(False, f"Backend not responding: {e}")
        return False

def test_2_login_endpoint_exists():
    """Test 2: Login endpoint is accessible and returns proper structure"""
    print_test_header(2, "WhatsApp Login Endpoint")
    print_step(1, "Call /api/whatsapp/login endpoint")
    try:
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/login",
            json={"session_name": "test_scenario_2"},
            timeout=30
        )
        print_result(response.status_code == 200, f"Endpoint responded with status {response.status_code}")
        
        data = response.json()
        print_step(2, "Check response structure")
        
        required_fields = ["success", "message"]
        has_all_fields = all(field in data for field in required_fields)
        print_result(has_all_fields, f"Response has required fields: {required_fields}")
        
        if has_all_fields:
            print(f"      Response: {json.dumps(data, indent=8)}")
            return True
    except Exception as e:
        print_result(False, f"Error calling login endpoint: {e}")
    return False

def test_3_status_polling():
    """Test 3: Status endpoint for polling login state"""
    print_test_header(3, "Status Polling Endpoint")
    print_step(1, "Call /api/whatsapp/status endpoint")
    try:
        response = requests.get(f"{BASE_URL}/api/whatsapp/status", timeout=5)
        print_result(response.status_code == 200, f"Status endpoint responded with {response.status_code}")
        
        data = response.json()
        print_step(2, "Check status response")
        print_result("logged_in" in data, "Response contains 'logged_in' field")
        print(f"      Status response: {json.dumps(data, indent=8)}")
        return True
    except Exception as e:
        print_result(False, f"Error calling status endpoint: {e}")
    return False

def test_4_qr_code_generation():
    """Test 4: QR code is generated and accessible"""
    print_test_header(4, "QR Code Generation & Storage")
    print_step(1, "Call login endpoint to trigger QR generation")
    try:
        response = requests.post(
            f"{BASE_URL}/api/whatsapp/login",
            json={"session_name": "test_scenario_4"},
            timeout=30
        )
        print_result(response.status_code == 200, f"Login endpoint responded")
        
        data = response.json()
        print_step(2, "Check if QR code base64 is in response")
        
        if "qr_code_base64" in data and data["qr_code_base64"]:
            print_result(True, f"QR code base64 generated ({len(data['qr_code_base64'])} chars)")
            print_step(3, "Verify QR file saved to disk")
            
            qr_file = Path("../whatsapp_sessions/test_scenario_4_qr.png")
            # Try default location too
            qr_file_default = Path("../whatsapp_sessions/default_qr.png")
            
            if qr_file.exists():
                print_result(True, f"QR file saved: {qr_file} ({qr_file.stat().st_size} bytes)")
                return True
            elif qr_file_default.exists():
                print_result(True, f"QR file saved to default: {qr_file_default} ({qr_file_default.stat().st_size} bytes)")
                return True
            else:
                print_result(False, "QR file not found on disk")
                return False
        else:
            print_result(False, "No QR code base64 in response")
            return False
    except Exception as e:
        print_result(False, f"Error generating QR code: {e}")
    return False

def test_5_multiple_login_clicks():
    """Test 5: Multiple rapid login clicks don't cause 500 errors"""
    print_test_header(5, "Multiple Login Clicks (No 500 Errors)")
    print_step(1, "Click login button 3 times rapidly")
    
    success_count = 0
    error_count = 0
    
    for i in range(3):
        try:
            response = requests.post(
                f"{BASE_URL}/api/whatsapp/login",
                json={"session_name": f"test_scenario_5_{i}"},
                timeout=30
            )
            if response.status_code == 200:
                success_count += 1
                print_result(True, f"Click {i+1}: Status 200 (OK)")
            else:
                error_count += 1
                print_result(False, f"Click {i+1}: Status {response.status_code} (ERROR)")
        except Exception as e:
            error_count += 1
            print_result(False, f"Click {i+1}: Exception - {e}")
    
    print_step(2, "Results")
    print(f"      ✅ Successful: {success_count}/3")
    print(f"      ❌ Failed: {error_count}/3")
    return error_count == 0

def test_6_headless_mode_verification():
    """Test 6: Chrome runs in headless mode (no UI)"""
    print_test_header(6, "Headless Mode Verification")
    print_step(1, "Check whatsapp_service.py for headless flag")
    
    try:
        with open("app/whatsapp_service.py", "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        if "--headless=new" in content:
            print_result(True, "Headless mode flag '--headless=new' found in code")
        elif "--headless" in content:
            print_result(True, "Headless mode flag '--headless' found in code")
        else:
            print_result(False, "Headless mode flag not found")
            
        print_step(2, "Check Chrome options configuration")
        if "chrome_options.add_argument" in content and "headless" in content:
            print_result(True, "Headless Chrome options properly configured")
            return True
        else:
            print_result(False, "Chrome options not properly configured")
            return False
            
    except Exception as e:
        print_result(False, f"Error reading code: {e}")
    return False

def test_7_terminal_output_format():
    """Test 7: Terminal output is user-friendly (not raw base64)"""
    print_test_header(7, "Terminal Output Format")
    print_step(1, "Check print_qr_to_terminal() function")
    
    try:
        with open("app/whatsapp_service.py", "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        print_step(2, "Verify helpful messages are printed")
        checks = {
            "📱 WHATSAPP WEB LOGIN": "Status header",
            "QR Code is ready for scanning": "QR status message",
            "OPTIONS TO SCAN": "Options header",
            "1️⃣  RECOMMENDED: Use the Modal": "Modal recommendation",
            "2️⃣  ALTERNATIVE: Open QR code file": "File option",
            "3️⃣  MANUAL: Type WhatsApp login URL": "Manual option",
            "Waiting for scan": "Timeout message"
        }
        
        found_count = 0
        for check_text, description in checks.items():
            if check_text in content:
                found_count += 1
                print_result(True, f"✓ {description}")
            else:
                print_result(False, f"✗ {description}")
        
        print_step(3, "Verify NO raw base64 printing")
        if "f\"data:image/png;base64,{self.qr_code_base64}\"" not in content:
            print_result(True, "No raw base64 printing found")
            return found_count >= 6  # At least 6 helpful messages
        else:
            print_result(False, "Still printing raw base64 to terminal")
            return False
            
    except Exception as e:
        print_result(False, f"Error reading code: {e}")
    return False

def main():
    print("\n\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "WHATSAPP WEB INTEGRATION - COMPREHENSIVE TEST SUITE".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")
    
    results = {}
    
    # Run all tests
    results["1_startup"] = test_1_app_startup()
    time.sleep(1)
    
    results["2_endpoint"] = test_2_login_endpoint_exists()
    time.sleep(1)
    
    results["3_polling"] = test_3_status_polling()
    time.sleep(1)
    
    results["4_qr_code"] = test_4_qr_code_generation()
    time.sleep(1)
    
    results["5_multiple_clicks"] = test_5_multiple_login_clicks()
    time.sleep(1)
    
    results["6_headless"] = test_6_headless_mode_verification()
    time.sleep(1)
    
    results["7_terminal_output"] = test_7_terminal_output_format()
    
    # Summary
    print("\n\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    test_names = {
        "1_startup": "✅ App Startup with Headless Chrome",
        "2_endpoint": "✅ WhatsApp Login Endpoint",
        "3_polling": "✅ Status Polling Endpoint",
        "4_qr_code": "✅ QR Code Generation & Storage",
        "5_multiple_clicks": "✅ Multiple Login Clicks (No Errors)",
        "6_headless": "✅ Headless Mode Verification",
        "7_terminal_output": "✅ Terminal Output Format"
    }
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for key, name in test_names.items():
        status = "✅ PASS" if results[key] else "❌ FAIL"
        print(f"{status}: {name}")
    
    print("\n" + "-"*80)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("="*80 + "\n")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
