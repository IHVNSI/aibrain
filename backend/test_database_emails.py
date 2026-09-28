#!/usr/bin/env python3
"""Check if emails are stored in the database."""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import StoredEmail, SentEmail, DraftEmail

print("=" * 60)
print("DATABASE EMAIL CHECK")
print("=" * 60)

try:
    app = create_app()
    with app.app_context():
        # Check stored emails
        stored_count = StoredEmail.query.count()
        print(f"\n📧 StoredEmail table:")
        print(f"   Total emails: {stored_count}")
        
        if stored_count > 0:
            stored_emails = StoredEmail.query.limit(5).all()
            print(f"   Recent emails:")
            for email in stored_emails:
                print(f"      - From: {email.from_address}")
                print(f"        Subject: {email.subject}")
                print(f"        Folder: {email.folder}")
                print(f"        Date: {email.received_date}")
        
        # Check sent emails
        sent_count = SentEmail.query.count()
        print(f"\n📤 SentEmail table:")
        print(f"   Total sent emails: {sent_count}")
        
        # Check draft emails
        draft_count = DraftEmail.query.count()
        print(f"\n📝 DraftEmail table:")
        print(f"   Total draft emails: {draft_count}")
        
        if draft_count > 0:
            drafts = DraftEmail.query.limit(3).all()
            print(f"   Recent drafts:")
            for draft in drafts:
                print(f"      - To: {draft.to_address}")
                print(f"        Subject: {draft.subject}")
                print(f"        Status: {draft.status}")
        
        print("\n" + "=" * 60)
        if stored_count == 0 and sent_count == 0 and draft_count == 0:
            print("⚠️  No emails found in database!")
            print("   This means:")
            print("   1. The automatic sync hasn't run yet, OR")
            print("   2. The sync task is not storing emails in the database")
        else:
            print("✅ Emails found in database!")
        
        print("=" * 60)
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
