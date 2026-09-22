#!/usr/bin/env python
"""
Migration script to create the sent_emails table for tracking outgoing emails.
Run this once to set up the table.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db
from app.models import SentEmail

def migrate():
    """Create the sent_emails table."""
    app = create_app()
    
    with app.app_context():
        print("Creating sent_emails table...")
        
        # Check if table already exists
        inspector = db.inspect(db.engine)
        if 'sent_emails' in inspector.get_table_names():
            print("✓ sent_emails table already exists")
            return
        
        # Create the table
        db.create_all()
        print("✓ sent_emails table created successfully")
        print("\nTable columns:")
        for column in SentEmail.__table__.columns:
            print(f"  - {column.name}: {column.type}")

if __name__ == '__main__':
    migrate()
