#!/usr/bin/env python
"""
Migration script: Create draft_emails and auto_reply_settings tables
"""
import sys
sys.path.insert(0, '.')

from app import create_app
from app.extensions import db

def migrate():
    """Create new email-related tables"""
    app = create_app()
    
    with app.app_context():
        print("Creating new email tables...")
        
        try:
            # Create the new tables
            db.create_all()
            print("✓ Tables created successfully")
            
            # Verify tables exist
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = ['draft_emails', 'auto_reply_settings']
            for table in required_tables:
                if table in tables:
                    print(f"✓ {table} created")
                else:
                    print(f"✗ {table} NOT created")
            
        except Exception as e:
            print(f"✗ Error creating tables: {e}")
            return False
    
    return True

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
