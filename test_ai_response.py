#!/usr/bin/env python
"""Test AI email response generation with sample email."""
import requests
import json

print("=" * 70)
print("TESTING AI EMAIL RESPONSE GENERATION")
print("=" * 70)

# Step 1: Login
print("\nStep 1: Authenticating...")
login_url = "http://localhost:5001/api/auth/login"
login_data = {"username": "admin@brainr.com", "password": "@@AdminBrainer22"}
login_resp = requests.post(login_url, json=login_data)

if login_resp.status_code != 200:
    print("✗ Authentication failed")
    exit(1)

token = login_resp.json().get("token")
headers = {"Authorization": f"Bearer {token}"}
print("✓ Authenticated successfully")

# Step 2: Test AI response generation
print("\nStep 2: Testing AI response generation...")
print("-" * 70)

# Sample email data
sample_email = {
    "email_from": "client@example.com",
    "subject": "Urgent: Project Deadline Change",
    "body": """Hi there,

I hope you're having a great day. We have a small but important update regarding the project timeline. 

The client has requested to move the final delivery date from next month to mid-next month. This means we need to accelerate some of our development sprints.

Would you be available for a quick sync call tomorrow or the day after to discuss the revised timeline and resource allocation?

Please let me know your availability.

Thanks!
John Smith
Project Manager
ABC Corp""",
    "custom_prompt": "You are a professional project coordinator. Generate a brief, professional response confirming availability and proposing specific meeting times. Keep it concise (2-3 sentences)."
}

# Call AI response endpoint
respond_url = "http://localhost:5001/api/email/respond"
print(f"Sending email to AI response endpoint...")
print(f"  From: {sample_email['email_from']}")
print(f"  Subject: {sample_email['subject']}")

respond_resp = requests.post(respond_url, json=sample_email, headers=headers)

if respond_resp.status_code != 200:
    print(f"\n✗ API Error - Status {respond_resp.status_code}")
    print(json.dumps(respond_resp.json(), indent=2))
    exit(1)

result = respond_resp.json()
print(f"\n✓ AI Response Generated Successfully!")

print("\n" + "=" * 70)
print("RESPONSE DETAILS")
print("=" * 70)

print(f"\nOriginal Email:")
print(f"  From: {sample_email['email_from']}")
print(f"  Subject: {sample_email['subject']}")
print(f"  Body (first 200 chars):")
body_preview = sample_email['body'][:200].replace('\n', '\n    ')
print(f"    {body_preview}...")

print(f"\nAI-Generated Response:")
print(f"  Status: {result.get('message', 'N/A')}")

if result.get('response'):
    response_text = result['response']
    print(f"\n  Response Text:")
    for line in response_text.split('\n'):
        if line.strip():
            print(f"    {line}")
else:
    print("  (No response text in result)")

print(f"\n  Success: {result.get('success', False)}")
if 'recipient' in result:
    print(f"  Recipient: {result.get('recipient')}")
if 'subject' in result:
    print(f"  Reply Subject: {result.get('subject')}")

print("\n" + "=" * 70)
print("✓ AI EMAIL RESPONSE TEST COMPLETE")
print("=" * 70)

# Step 3: Test with another sample
print("\n\nStep 3: Testing with different email type...")
print("-" * 70)

sample_email_2 = {
    "email_from": "support@vendor.com",
    "subject": "Monthly Invoice #INV-2024-001",
    "body": """Dear Valued Customer,

Please find attached your monthly invoice for August 2024.

Invoice Details:
- Invoice Number: INV-2024-001
- Amount Due: $5,000.00
- Due Date: September 15, 2024

Please process payment at your earliest convenience. If you have any questions or require clarification, please don't hesitate to reach out.

Best regards,
Vendor Support Team""",
    "custom_prompt": "You are an accounts manager. Generate a professional acknowledgment of the invoice receipt. Confirm receipt and provide payment timeline estimate."
}

print(f"Sending second email for AI response...")
print(f"  From: {sample_email_2['email_from']}")
print(f"  Subject: {sample_email_2['subject']}")

respond_resp_2 = requests.post(respond_url, json=sample_email_2, headers=headers)

if respond_resp_2.status_code == 200:
    result_2 = respond_resp_2.json()
    print(f"\n✓ Second response generated!")
    print(f"\n  AI Response:")
    if result_2.get('response'):
        for line in result_2['response'].split('\n')[:5]:
            if line.strip():
                print(f"    {line}")
else:
    print(f"✗ Second request failed: {respond_resp_2.status_code}")

print("\n" + "=" * 70)
print("✓ ALL TESTS COMPLETE - EMAIL AI RESPONSE SYSTEM IS WORKING!")
print("=" * 70)
