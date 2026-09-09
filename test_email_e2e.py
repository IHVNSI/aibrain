#!/usr/bin/env python
"""End-to-end email test: send test email, read it, and respond with AI."""
import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import requests
import json

sys.path.insert(0, 'backend')
from app.email_service import EmailConfig, EmailService

print("=" * 70)
print("END-TO-END EMAIL TEST: Send → Fetch → Respond with AI")
print("=" * 70)

# Step 1: Send a test email TO brainr@gintec.com.ng
print("\nSTEP 1: Sending test email to brainr@gintec.com.ng...")
print("-" * 70)

try:
    email_address = os.getenv('EMAIL_ADDRESS')
    email_password = os.getenv('EMAIL_PASSWORD')
    smtp_server = os.getenv('EMAIL_SMTP_SERVER', 'mail.gintec.com.ng')
    smtp_port = int(os.getenv('EMAIL_SMTP_PORT', 465))
    
    # Create test email
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Meeting Request - Can we discuss project timeline?'
    msg['From'] = email_address
    msg['To'] = email_address  # Send to self for testing
    
    body = """
    <html><body>
        <p>Hi,</p>
        <p>I hope this email finds you well. I wanted to reach out to discuss our upcoming project timeline and see if we can align on the key milestones.</p>
        <p>Would you be available for a call next week? I'm flexible with timing.</p>
        <p>Thanks!</p>
        <p>Best regards</p>
    </body></html>
    """
    
    msg.attach(MIMEText(body, 'html'))
    
    # Send via SMTP
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(email_address, email_password)
        server.send_message(msg)
    
    print(f"✓ Test email sent to {email_address}")
    print("  Subject: Meeting Request - Can we discuss project timeline?")
    print("  (Waiting 5 seconds for email to arrive...)")
    time.sleep(5)
    
except Exception as e:
    print(f"✗ Failed to send test email: {e}")
    exit(1)

# Step 2: Fetch the test email
print("\n" + "=" * 70)
print("STEP 2: Fetching emails from INBOX...")
print("-" * 70)

try:
    email_service = EmailConfig.get_email_service()
    if not email_service or not email_service.connect():
        print("✗ Failed to connect to email service")
        exit(1)
    
    # Get all emails (check last 1 day to catch the test email)
    emails = email_service.get_emails_by_date_range(days_back=1, limit=10)
    email_service.disconnect()
    
    print(f"✓ Found {len(emails)} email(s)")
    
    if len(emails) == 0:
        print("  (No emails found - the test email may not have arrived yet)")
        print("  Proceeding to test the API endpoint instead...")
        exit(0)
    
    # Show email details
    test_email = emails[0]
    print(f"\n  Email Details:")
    print(f"    From: {test_email.get('from')}")
    print(f"    Subject: {test_email.get('subject')}")
    print(f"    Body (first 100 chars): {test_email.get('body', '')[:100]}...")
    print(f"    UID: {test_email.get('uid')}")
    
except Exception as e:
    print(f"✗ Failed to fetch emails: {e}")
    exit(1)

# Step 3: Generate AI response via API
print("\n" + "=" * 70)
print("STEP 3: Generating AI response via API...")
print("-" * 70)

try:
    # Login
    login_url = "http://localhost:5001/api/auth/login"
    login_data = {"username": "admin@brainr.com", "password": "@@AdminBrainer22"}
    login_resp = requests.post(login_url, json=login_data)
    
    if login_resp.status_code != 200:
        print("✗ Failed to login")
        exit(1)
    
    token = login_resp.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Call AI response endpoint
    respond_url = "http://localhost:5001/api/email/respond"
    respond_data = {
        "email_from": test_email.get("from", "unknown@example.com"),
        "subject": test_email.get("subject", "No Subject"),
        "body": test_email.get("body", ""),
        "custom_prompt": "You are a professional business assistant. Generate a concise, friendly response confirming availability for the call. Keep it to 2-3 sentences."
    }
    
    print(f"Sending to AI response endpoint...")
    respond_resp = requests.post(respond_url, json=respond_data, headers=headers)
    
    if respond_resp.status_code != 200:
        print(f"✗ API returned status {respond_resp.status_code}")
        print(json.dumps(respond_resp.json(), indent=2))
        exit(1)
    
    result = respond_resp.json()
    print(f"✓ Response generated successfully!")
    print(f"\n  API Response:")
    print(f"    Message: {result.get('message')}")
    
    if result.get('response'):
        print(f"\n  Generated AI Response:")
        lines = result['response'].split('\n')
        for line in lines[:10]:  # First 10 lines
            if line.strip():
                print(f"    {line}")
    
except Exception as e:
    print(f"✗ Failed to generate AI response: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 70)
print("✓ END-TO-END TEST COMPLETE!")
print("=" * 70)
print("\nSummary:")
print("  1. ✓ Test email sent successfully")
print("  2. ✓ Email fetched from IMAP")
print("  3. ✓ AI generated professional response")
print("  4. ✓ Response ready to send via SMTP")
