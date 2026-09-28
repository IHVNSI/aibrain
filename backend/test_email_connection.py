#!/usr/bin/env python3
"""Test email connection with current .env configuration."""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from app.email_service import EmailConfig

print("=" * 60)
print("EMAIL CONNECTION TEST")
print("=" * 60)

# Print configuration
print(f"\n📋 Configuration:")
print(f"  EMAIL_ADDRESS: {os.getenv('EMAIL_ADDRESS')}")
print(f"  EMAIL_PROVIDER: {os.getenv('EMAIL_PROVIDER')}")
print(f"  EMAIL_IMAP_SERVER: {os.getenv('EMAIL_IMAP_SERVER')}")
print(f"  EMAIL_IMAP_PORT: {os.getenv('EMAIL_IMAP_PORT')}")
print(f"  EMAIL_PASSWORD: {'*' * len(os.getenv('EMAIL_PASSWORD', ''))}")

# Try to get email service
print(f"\n🔌 Attempting connection...")
try:
    email_service = EmailConfig.get_email_service()
    
    if email_service is None:
        print("❌ Failed: Email service is None - check connection details")
        sys.exit(1)
    
    print("✅ Connected successfully!")
    
    # Try to list folders
    print(f"\n📁 Listing mailbox folders...")
    try:
        folders = email_service.mailbox.folder.list()
        print(f"✅ Found {len(folders)} folders:")
        for folder in folders:
            print(f"    - {folder.name}")
    except Exception as e:
        print(f"❌ Failed to list folders: {e}")
    
    # Try to get unread emails
    print(f"\n📧 Fetching unread emails from INBOX...")
    try:
        unread = email_service.get_unread_emails(limit=5)
        if unread:
            print(f"✅ Found {len(unread)} unread emails:")
            for email in unread[:3]:
                print(f"    - From: {email.get('from', 'Unknown')}")
                print(f"      Subject: {email.get('subject', '(no subject)')}")
        else:
            print(f"⚠️  No unread emails found")
    except Exception as e:
        print(f"❌ Failed to fetch unread emails: {e}")
    
    # Try to get all emails
    print(f"\n📥 Fetching all emails from INBOX (limit: 10)...")
    try:
        all_emails = email_service.get_all_emails(folder='INBOX', limit=10)
        if all_emails:
            print(f"✅ Found {len(all_emails)} emails (total in INBOX may be more):")
            for email in all_emails[:3]:
                print(f"    - From: {email.get('from', 'Unknown')}")
                print(f"      Subject: {email.get('subject', '(no subject)')}")
        else:
            print(f"⚠️  No emails found in INBOX")
    except Exception as e:
        print(f"❌ Failed to fetch all emails: {e}")
    
    # Disconnect
    email_service.disconnect()
    print(f"\n✓ Disconnected")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ TEST COMPLETE")
print("=" * 60)
