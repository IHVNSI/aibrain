#!/usr/bin/env python3
"""Manually trigger email sync and check database."""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import StoredEmail
from app.email_service import EmailConfig

print("=" * 60)
print("MANUAL EMAIL SYNC TEST")
print("=" * 60)

try:
    app = create_app()
    
    with app.app_context():
        print("\n🔌 Getting email service...")
        email_service = EmailConfig.get_email_service()
        
        if not email_service:
            print("❌ Failed to connect to email service")
            sys.exit(1)
        
        print("✅ Connected to email service")
        
        # Download emails
        print("\n📥 Downloading emails...")
        emails = email_service.get_all_emails(folder='INBOX', limit=500)
        print(f"✅ Downloaded {len(emails)} emails")
        
        if not emails:
            print("⚠️  No emails to process")
            sys.exit(0)
        
        # Disconnect
        email_service.disconnect()
        print("✓ Disconnected")
        
        # Process and store emails
        print(f"\n💾 Storing emails in database...")
        new_emails_count = 0
        
        for email_data in emails:
            print(f"\n  Processing email from: {email_data.get('from', 'Unknown')}")
            print(f"  Subject: {email_data.get('subject', '(no subject)')}")
            print(f"  UID: {email_data.get('id')}")
            
            # Check if already exists
            existing = StoredEmail.query.filter_by(email_uid=email_data.get('id')).first()
            if existing:
                print(f"  ⚠️  Already stored")
                continue
            
            try:
                # Parse date
                from datetime import datetime
                try:
                    received_dt = datetime.fromisoformat(email_data.get('date'))
                except (ValueError, TypeError):
                    received_dt = datetime.now()
                
                # Create email record
                stored_email = StoredEmail(
                    email_uid=email_data.get('id'),
                    from_address=email_data.get('from', ''),
                    subject=email_data.get('subject', ''),
                    body=email_data.get('text', ''),
                    html_body=email_data.get('html', ''),
                    received_date=received_dt,
                    is_read=False,
                    folder='INBOX'
                )
                
                db.session.add(stored_email)
                db.session.flush()
                new_emails_count += 1
                print(f"  ✅ Added to database")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                import traceback
                traceback.print_exc()
        
        # Commit
        print(f"\n📤 Committing {new_emails_count} emails...")
        try:
            db.session.commit()
            print(f"✅ Committed successfully!")
        except Exception as commit_err:
            print(f"❌ Commit error: {commit_err}")
            db.session.rollback()
            sys.exit(1)
        
        # Verify
        print(f"\n📊 Verifying database...")
        total_stored = StoredEmail.query.count()
        print(f"   Total StoredEmail records: {total_stored}")
        
        stored_emails = StoredEmail.query.limit(5).all()
        if stored_emails:
            print(f"   Recent emails:")
            for email in stored_emails:
                print(f"      - {email.from_address}: {email.subject}")
        
        print("\n" + "=" * 60)
        print("✅ MANUAL SYNC COMPLETE")
        print("=" * 60)
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
