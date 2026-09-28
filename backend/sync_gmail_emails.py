#!/usr/bin/env python3
"""Quick script to sync emails from Gmail to database."""
import sys
import os
from datetime import datetime
from dateutil import parser as dateutil_parser

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.extensions import db
from app import create_app
from app.models import StoredEmail
from app.email_service import EmailConfig

def sync_emails():
    """Sync emails from Gmail IMAP to database."""
    app = create_app()
    
    with app.app_context():
        print("🔄 Connecting to Gmail IMAP...")
        email_service = EmailConfig.get_email_service()
        
        if not email_service:
            print("❌ Failed to connect to Gmail IMAP")
            return
        
        print("✅ Connected to Gmail")
        print("📥 Fetching emails from INBOX...")
        
        try:
            # Get all emails from INBOX
            emails = email_service.get_all_emails('INBOX', limit=50)
            print(f"📊 Retrieved {len(emails)} emails from Gmail")
            
            if not emails:
                print("⚠️  No emails found in Gmail INBOX")
                return
            
            # Store emails in database
            stored_count = 0
            skipped_count = 0
            
            for email in emails:
                try:
                    # Check if email already exists
                    email_uid = email.get('id', '')
                    existing = StoredEmail.query.filter_by(
                        email_uid=email_uid,
                        folder='INBOX'
                    ).first()
                    
                    if existing:
                        skipped_count += 1
                        continue
                    
                    # Parse date if it's a string
                    received_date = email.get('date')
                    if isinstance(received_date, str):
                        try:
                            received_date = dateutil_parser.isoparse(received_date)
                        except:
                            received_date = datetime.utcnow()
                    elif not isinstance(received_date, datetime):
                        received_date = datetime.utcnow()
                    
                    # Create new stored email
                    stored_email = StoredEmail(
                        email_uid=email_uid,
                        subject=email.get('subject', '(no subject)'),
                        from_address=email.get('from', 'unknown'),
                        received_date=received_date,
                        body=email.get('text', ''),
                        html_body=email.get('html', ''),
                        is_read=email.get('is_read', False),
                        folder='INBOX',
                        is_new=True,
                        auto_reply_sent=False
                    )
                    
                    db.session.add(stored_email)
                    stored_count += 1
                    
                except Exception as e:
                    print(f"⚠️  Error storing email: {e}")
                    continue
            
            # Commit all changes
            if stored_count > 0:
                db.session.commit()
                print(f"✅ Stored {stored_count} new emails in database")
            
            if skipped_count > 0:
                print(f"⏭️  Skipped {skipped_count} emails (already in database)")
            
            print(f"\n📈 Summary:")
            print(f"   - Gmail INBOX: {len(emails)} emails")
            print(f"   - Stored in DB: {stored_count} emails")
            print(f"   - Skipped: {skipped_count} emails")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            email_service.disconnect()
            print("🔌 Disconnected from Gmail")

if __name__ == '__main__':
    sync_emails()
