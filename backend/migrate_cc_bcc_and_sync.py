#!/usr/bin/env python3
"""
Migration: Add CC/BCC columns to draft_emails and sent_emails tables,
and create last_email_sync table for duplicate prevention tracking.
"""
import os
import sys
from sqlalchemy import Column, String, Integer, DateTime, text
from datetime import datetime

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Change to backend directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import DraftEmail, SentEmail, LastEmailSync

# Create app context
app = create_app()

def migrate():
    """Run the migration."""
    with app.app_context():
        # Check if we're using SQLite
        connection = db.engine.connect()
        
        try:
            # Check if cc_address column exists in draft_emails
            print("Checking draft_emails table for CC/BCC columns...")
            result = connection.execute(text("PRAGMA table_info(draft_emails)"))
            columns = [row[1] for row in result]
            
            if 'cc_address' not in columns:
                print("Adding cc_address column to draft_emails...")
                connection.execute(text("ALTER TABLE draft_emails ADD COLUMN cc_address VARCHAR(500)"))
                connection.commit()
                print("✓ Added cc_address to draft_emails")
            else:
                print("✓ cc_address already exists in draft_emails")
            
            if 'bcc_address' not in columns:
                print("Adding bcc_address column to draft_emails...")
                connection.execute(text("ALTER TABLE draft_emails ADD COLUMN bcc_address VARCHAR(500)"))
                connection.commit()
                print("✓ Added bcc_address to draft_emails")
            else:
                print("✓ bcc_address already exists in draft_emails")
            
            # Check if cc_address column exists in sent_emails
            print("\nChecking sent_emails table for CC/BCC columns...")
            result = connection.execute(text("PRAGMA table_info(sent_emails)"))
            columns = [row[1] for row in result]
            
            if 'cc_address' not in columns:
                print("Adding cc_address column to sent_emails...")
                connection.execute(text("ALTER TABLE sent_emails ADD COLUMN cc_address VARCHAR(500)"))
                connection.commit()
                print("✓ Added cc_address to sent_emails")
            else:
                print("✓ cc_address already exists in sent_emails")
            
            if 'bcc_address' not in columns:
                print("Adding bcc_address column to sent_emails...")
                connection.execute(text("ALTER TABLE sent_emails ADD COLUMN bcc_address VARCHAR(500)"))
                connection.commit()
                print("✓ Added bcc_address to sent_emails")
            else:
                print("✓ bcc_address already exists in sent_emails")
            
            # Check if last_email_sync table exists
            print("\nChecking last_email_sync table...")
            result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='last_email_sync'"))
            if not result.fetchone():
                print("Creating last_email_sync table...")
                db.create_all()
                print("✓ Created last_email_sync table")
            else:
                print("✓ last_email_sync table already exists")
            
            connection.close()
            print("\n✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            connection.close()
            sys.exit(1)

if __name__ == '__main__':
    migrate()
