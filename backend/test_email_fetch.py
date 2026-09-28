#!/usr/bin/env python3
"""
Test script to diagnose email fetching issues.
Run from backend directory: python test_email_fetch.py
"""

import sys
import os
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

# Import email service
try:
    from app.email_service import EmailService
    logger.info("✓ EmailService imported successfully")
except Exception as e:
    logger.error(f"✗ Failed to import EmailService: {e}")
    sys.exit(1)

# Test email fetching
def test_email_fetch():
    """Test fetching emails from IMAP."""
    print("\n" + "="*60)
    print("EMAIL FETCH TEST")
    print("="*60 + "\n")
    
    # Check environment variables
    print("[1/6] Checking environment variables...")
    imap_server = os.getenv('IMAP_SERVER')
    imap_email = os.getenv('IMAP_EMAIL')
    imap_password = os.getenv('IMAP_PASSWORD')
    
    if not all([imap_server, imap_email, imap_password]):
        print(f"✗ Missing credentials:")
        print(f"  IMAP_SERVER: {imap_server or 'NOT SET'}")
        print(f"  IMAP_EMAIL: {imap_email or 'NOT SET'}")
        print(f"  IMAP_PASSWORD: {'***' if imap_password else 'NOT SET'}")
        return False
    
    print(f"✓ Credentials found:")
    print(f"  IMAP_SERVER: {imap_server}")
    print(f"  IMAP_EMAIL: {imap_email}")
    
    # Create email service
    print("\n[2/6] Creating EmailService instance...")
    try:
        email_service = EmailService(
            server=imap_server,
            email=imap_email,
            password=imap_password
        )
        print("✓ EmailService instance created")
    except Exception as e:
        print(f"✗ Failed to create EmailService: {e}")
        return False
    
    # Connect to IMAP
    print("\n[3/6] Connecting to IMAP server...")
    try:
        email_service.connect()
        print("✓ Connected to IMAP server")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return False
    
    # Get folder list
    print("\n[4/6] Getting folder list...")
    try:
        folders = email_service.get_folder_list()
        print(f"✓ Found {len(folders)} folders:")
        for folder in folders[:10]:  # Show first 10
            print(f"    - {folder}")
        if len(folders) > 10:
            print(f"    ... and {len(folders) - 10} more folders")
    except Exception as e:
        print(f"✗ Failed to get folders: {e}")
        return False
    
    # Fetch all emails from INBOX
    print("\n[5/6] Fetching emails from INBOX...")
    try:
        emails = email_service.get_all_emails(folder='INBOX', limit=100)
        print(f"✓ Fetched {len(emails)} emails from INBOX")
        
        if emails:
            print("\nFirst 5 emails:")
            for i, email in enumerate(emails[:5], 1):
                print(f"\n  Email {i}:")
                print(f"    ID: {email.get('id')}")
                print(f"    From: {email.get('from')}")
                print(f"    Subject: {email.get('subject')}")
                print(f"    Date: {email.get('date')}")
                print(f"    Unread: {email.get('is_unread')}")
        else:
            print("  No emails found in INBOX")
    except Exception as e:
        print(f"✗ Failed to fetch emails: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Try [Gmail]/All Mail folder
    print("\n[6/6] Fetching emails from [Gmail]/All Mail...")
    try:
        emails_all = email_service.get_all_emails(folder='[Gmail]/All Mail', limit=100)
        print(f"✓ Fetched {len(emails_all)} emails from [Gmail]/All Mail")
        
        if emails_all:
            print(f"  First email: {emails_all[0].get('subject')}")
    except Exception as e:
        print(f"⚠ Note: Could not fetch from [Gmail]/All Mail: {e}")
    
    # Disconnect
    try:
        email_service.disconnect()
        print("\n✓ Disconnected from IMAP server")
    except:
        pass
    
    print("\n" + "="*60)
    print("TEST COMPLETED")
    print("="*60 + "\n")
    return True

if __name__ == '__main__':
    success = test_email_fetch()
    sys.exit(0 if success else 1)
