#!/usr/bin/env python
"""Database migration to create StoredEmail table for email storage."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db

def migrate():
    """Create StoredEmail table."""
    app = create_app()
    with app.app_context():
        print("[*] Running database migration...")
        
        # Create all tables
        db.create_all()
        
        print("[+] Database tables created successfully")
        print("\nCreated/Updated tables:")
        print("  - user_companies")
        print("  - branches")
        print("  - branch_admins")
        print("  - users")
        print("  - conversation")
        print("  - message")
        print("  - vanna_training")
        print("  - user_settings")
        print("  - stored_emails (NEW)")
        print("  - voice_training")
        print("\n[OK] Ready to use!")
        
        return 0

if __name__ == "__main__":
    sys.exit(migrate())
