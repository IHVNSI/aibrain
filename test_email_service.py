#!/usr/bin/env python
"""Test IMAP connection directly."""
import os
import sys
sys.path.insert(0, 'backend')

from app.email_service import EmailConfig, EmailService

print("=" * 60)
print("TESTING EMAIL CONFIGURATION")
print("=" * 60)

# Check environment variables
print("\nEmail Configuration from .env:")
print(f"  EMAIL_ADDRESS: {os.getenv('EMAIL_ADDRESS')}")
print(f"  EMAIL_PROVIDER: {os.getenv('EMAIL_PROVIDER')}")
print(f"  EMAIL_IMAP_SERVER: {os.getenv('EMAIL_IMAP_SERVER')}")
print(f"  EMAIL_IMAP_PORT: {os.getenv('EMAIL_IMAP_PORT')}")
print(f"  EMAIL_IMAP_TLS: {os.getenv('EMAIL_IMAP_TLS')}")

# Test email service
print("\n" + "=" * 60)
print("TESTING IMAP CONNECTION")
print("=" * 60)

try:
    email_service = EmailConfig.get_email_service()
    if not email_service:
        print("✗ Failed to initialize email service")
        exit(1)
    
    print("✓ Email service initialized")
    
    # Connect
    if email_service.connect():
        print("✓ Connected to IMAP server")
    else:
        print("✗ Failed to connect to IMAP server")
        exit(1)
    
    # Get folders
    print("\nFetching available folders...")
    folders = email_service.get_folder_list()
    print(f"✓ Available folders: {folders}")
    
    # Get all emails (not just unread)
    print("\nFetching ALL emails from past 30 days...")
    all_emails = email_service.get_emails_by_date_range(days_back=30, limit=20)
    print(f"✓ Total emails: {len(all_emails)}")
    
    for i, email in enumerate(all_emails[:5], 1):  # Show first 5
        print(f"\n  Email #{i}:")
        print(f"    From: {email.get('from')}")
        print(f"    Subject: {email.get('subject')}")
        print(f"    Date: {email.get('date')}")
        print(f"    Is Read: {email.get('is_read')}")
    
    # Get unread emails
    print("\n" + "-" * 60)
    print("Fetching UNREAD emails...")
    unread_emails = email_service.get_unread_emails(limit=20)
    print(f"✓ Unread emails: {len(unread_emails)}")
    
    for i, email in enumerate(unread_emails[:5], 1):
        print(f"\n  Unread Email #{i}:")
        print(f"    From: {email.get('from')}")
        print(f"    Subject: {email.get('subject')}")
        print(f"    Preview: {email.get('body', '')[:100]}")
    
    # Disconnect
    email_service.disconnect()
    print("\n✓ Disconnected from IMAP server")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 60)
print("✓ Email system test complete")
print("=" * 60)
