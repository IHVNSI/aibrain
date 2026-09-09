#!/usr/bin/env python
"""
Database migration script to add voice_training table.
Run this once to create the table if it doesn't exist.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import VoiceTraining

def migrate():
    """Create the voice_training table if it doesn't exist."""
    app = create_app()
    
    with app.app_context():
        try:
            # Create the table
            db.create_all()
            
            # Check if table was created
            if db.engine.dialect.has_table(db.engine.connect(), 'voice_training'):
                print("✓ voice_training table created successfully!")
                print("\nTable columns:")
                for col in VoiceTraining.__table__.columns:
                    print(f"  - {col.name}: {col.type}")
            else:
                print("✗ Failed to create voice_training table")
                return False
                
            return True
            
        except Exception as e:
            print(f"✗ Migration error: {e}")
            return False

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
