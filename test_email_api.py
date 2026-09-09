#!/usr/bin/env python
"""Test email API endpoints."""
import requests
import json

# Step 1: Login to get JWT token
print("=" * 60)
print("STEP 1: Login to get JWT token")
print("=" * 60)
login_url = "http://localhost:5001/api/auth/login"
login_data = {"username": "admin@brainr.com", "password": "@@AdminBrainer22"}
login_resp = requests.post(login_url, json=login_data)
print(f"Status: {login_resp.status_code}")

if login_resp.status_code != 200:
    print("Login failed!")
    print(json.dumps(login_resp.json(), indent=2))
    exit(1)

login_json = login_resp.json()
token = login_json.get("token")
print(f"✓ Token obtained: {token[:50]}...\n")

# Step 2: Get unread emails
print("=" * 60)
print("STEP 2: Fetch unread emails")
print("=" * 60)
headers = {"Authorization": f"Bearer {token}"}
unread_url = "http://localhost:5001/api/email/unread?limit=10"
unread_resp = requests.get(unread_url, headers=headers)
print(f"Status: {unread_resp.status_code}")

if unread_resp.status_code != 200:
    print("Unread emails fetch failed!")
    print(json.dumps(unread_resp.json(), indent=2))
    exit(1)

response_data = unread_resp.json()
print(json.dumps(response_data, indent=2))

# Extract emails list from response
emails = response_data.get("emails", []) if isinstance(response_data, dict) else response_data

if not emails or len(emails) == 0:
    print("\n✓ No unread emails found")
    exit(0)

print(f"\n✓ Found {len(emails)} unread email(s)")

# Step 3: Generate AI responses for each email
print("\n" + "=" * 60)
print("STEP 3: Generate AI responses")
print("=" * 60)

for i, email in enumerate(emails, 1):
    print(f"\n--- Email #{i} ---")
    email_from = email.get("from", "unknown@example.com")
    subject = email.get("subject", "No Subject")
    body = email.get("body", "")[:100] + "..." if len(email.get("body", "")) > 100 else email.get("body", "")
    
    print(f"From: {email_from}")
    print(f"Subject: {subject}")
    print(f"Body (preview): {body}\n")
    
    # Call AI response endpoint
    respond_url = "http://localhost:5001/api/email/respond"
    respond_data = {
        "email_from": email_from,
        "subject": subject,
        "body": email.get("body", ""),
        "custom_prompt": "Be professional and helpful. Keep response concise."
    }
    
    respond_resp = requests.post(respond_url, json=respond_data, headers=headers)
    print(f"Response Status: {respond_resp.status_code}")
    
    if respond_resp.status_code != 200:
        print(f"Failed to generate response:")
        print(json.dumps(respond_resp.json(), indent=2))
    else:
        result = respond_resp.json()
        print(f"AI Response Generated:")
        print(f"  Message: {result.get('message', 'N/A')}")
        if 'response' in result:
            print(f"  Generated Response:\n    {result['response']}")

print("\n" + "=" * 60)
print("✓ Email processing complete!")
print("=" * 60)
