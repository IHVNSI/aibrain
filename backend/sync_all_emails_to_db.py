#!/usr/bin/env python
"""
Quick script to sync all emails from the configured email account to the database.
Run this to populate the database with all emails before testing the app.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.email_service import EmailConfig
from app.extensions import db
from app.models import StoredEmail
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_all_emails():
    """Sync all emails from IMAP to database."""
    app = create_app()
    
    with app.app_context():
        logger.info("=" * 60)
        logger.info("SYNCING ALL EMAILS FROM IMAP SERVER TO DATABASE")
        logger.info("=" * 60)
        
        # Get email service
        email_service = EmailConfig.get_email_service()
        if not email_service:
            logger.error("Email service not configured. Set EMAIL_ADDRESS, EMAIL_PASSWORD, EMAIL_IMAP_SERVER in .env")
            return False
        
        try:
            # Get all folders
            folders = email_service.get_folders()
            logger.info(f"Found {len(folders)} folders: {folders}")
            
            total_synced = 0
            
            # Sync each folder
            for folder in folders:
                logger.info(f"\nSyncing folder: {folder}")
                
                try:
                    # Get emails from this folder
                    emails = email_service.get_emails_by_date_range(days_back=90, limit=500, folder=folder)
                    logger.info(f"  Retrieved {len(emails)} emails from {folder}")
                    
                    # Store in database
                    stored_count = 0
                    for email in emails:
                        # Check if already exists
                        existing = StoredEmail.query.filter_by(email_uid=email['id']).first()
                        if not existing:
                            try:
                                received_dt = datetime.fromisoformat(email['date']) if email.get('date') else datetime.now()
                            except:
                                received_dt = datetime.now()
                            
                            stored_email = StoredEmail(
                                email_uid=email['id'],
                                from_address=email.get('from', ''),
                                subject=email.get('subject', ''),
                                body=email.get('text', ''),
                                html_body=email.get('html', ''),
                                received_date=received_dt,
                                is_read=not email.get('is_unread', False),
                                folder=folder
                            )
                            db.session.add(stored_email)
                            stored_count += 1
                    
                    if stored_count > 0:
                        db.session.commit()
                        logger.info(f"  Stored {stored_count} new emails from {folder}")
                        total_synced += stored_count
                
                except Exception as e:
                    logger.error(f"Error syncing folder {folder}: {e}")
                    db.session.rollback()
            
            logger.info(f"\n✓ SYNC COMPLETE: {total_synced} new emails stored in database")
            return True
        
        except Exception as e:
            logger.error(f"Error syncing emails: {e}", exc_info=True)
            return False
        
        finally:
            try:
                email_service.disconnect()
            except:
                pass

if __name__ == '__main__':
    success = sync_all_emails()
    sys.exit(0 if success else 1)
