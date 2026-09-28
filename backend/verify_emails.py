#!/usr/bin/env python3
"""Test script to verify emails are loaded and accessible."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.extensions import db
from app import create_app
from app.models import StoredEmail

def verify_emails():
    """Verify emails are in the database."""
    app = create_app()
    
    with app.app_context():
        # Count total emails
        total = StoredEmail.query.count()
        inbox = StoredEmail.query.filter_by(folder='INBOX').count()
        
        print(f"📊 Email Database Status:")
        print(f"   - Total emails: {total}")
        print(f"   - INBOX emails: {inbox}")
        
        if inbox > 0:
            print(f"\n📧 Sample emails from INBOX:")
            emails = StoredEmail.query.filter_by(folder='INBOX').limit(5).all()
            
            for i, email in enumerate(emails, 1):
                print(f"\n   Email {i}:")
                print(f"   - From: {email.from_address}")
                print(f"   - Subject: {email.subject}")
                print(f"   - Date: {email.received_date}")
                print(f"   - Read: {email.is_read}")
                print(f"   - Preview: {email.body[:50]}...")
        else:
            print("\n⚠️  No emails found in INBOX!")

if __name__ == '__main__':
    verify_emails()
