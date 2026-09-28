#!/usr/bin/env python
"""
Migration script: Add email sync status tracking and new email flags.

This script:
1. Creates the email_sync_status table
2. Adds is_new and auto_reply_sent columns to stored_emails table
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models import EmailSyncStatus, StoredEmail
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """Run migration."""
    logger.info("=" * 60)
    logger.info("MIGRATION: Email Sync Status & New Email Tracking")
    logger.info("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Create tables
            logger.info("Creating tables...")
            db.create_all()
            logger.info("  ✓ All tables created/verified")
            
            # Check if columns exist
            from sqlalchemy import inspect
            
            inspector = inspect(db.engine)
            stored_email_columns = [col['name'] for col in inspector.get_columns('stored_emails')]
            
            # Add is_new column if it doesn't exist
            if 'is_new' not in stored_email_columns:
                logger.info("Adding is_new column to stored_emails...")
                db.session.execute(
                    text('ALTER TABLE stored_emails ADD COLUMN is_new BOOLEAN DEFAULT TRUE')
                )
                db.session.commit()
                logger.info("  ✓ is_new column added")
            else:
                logger.info("  ✓ is_new column already exists")
            
            # Add auto_reply_sent column if it doesn't exist
            if 'auto_reply_sent' not in stored_email_columns:
                logger.info("Adding auto_reply_sent column to stored_emails...")
                db.session.execute(
                    text('ALTER TABLE stored_emails ADD COLUMN auto_reply_sent BOOLEAN DEFAULT FALSE')
                )
                db.session.commit()
                logger.info("  ✓ auto_reply_sent column added")
            else:
                logger.info("  ✓ auto_reply_sent column already exists")
            
            logger.info("=" * 60)
            logger.info("Migration completed successfully!")
            logger.info("=" * 60)
            logger.info("")
            logger.info("New features:")
            logger.info("  - Full email sync via /api/email/sync/full")
            logger.info("  - Continuous sync via /api/email/sync/continuous/start")
            logger.info("  - Auto-reply for new emails only")
            logger.info("  - Sync status tracking at /api/email/sync/status")
            logger.info("")
        
        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            return False
    
    return True

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
