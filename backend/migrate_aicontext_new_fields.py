#!/usr/bin/env python3
"""
Migration script to add new fields to AIContext table.

This adds three new optional text fields to support channel-specific response rules:
- email_response_rules: Email-specific AI response instructions
- whatsapp_response_rules: WhatsApp-specific AI response instructions  
- parent_app_description: Description of application structure for AI understanding

Run with: python migrate_aicontext_new_fields.py
"""
import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir.parent))

def migrate():
    """Add new columns to AIContext table."""
    from app import create_app
    from app.extensions import db
    from sqlalchemy import text
    
    app = create_app()
    
    with app.app_context():
        try:
            # Get the database URL to determine dialect
            db_url = os.getenv('DATABASE_URL', '')
            is_sqlite = 'sqlite' in db_url or not db_url
            is_mysql = 'mysql' in db_url
            is_postgres = 'postgresql' in db_url or 'postgres' in db_url
            
            print("=" * 70)
            print("AIContext Migration: Adding email/WhatsApp response rules fields")
            print("=" * 70)
            
            with db.engine.connect() as conn:
                # Check if columns already exist
                inspector = db.inspect(db.engine)
                existing_columns = {col['name'] for col in inspector.get_columns('ai_context')}
                
                new_fields = [
                    ('email_response_rules', 'Email response rules'),
                    ('whatsapp_response_rules', 'WhatsApp response rules'),
                    ('parent_app_description', 'Parent app description'),
                ]
                
                for field_name, description in new_fields:
                    if field_name in existing_columns:
                        print(f"✅ Column '{field_name}' already exists - skipping")
                        continue
                    
                    # Add column based on database dialect
                    if is_sqlite:
                        sql = f"ALTER TABLE ai_context ADD COLUMN {field_name} TEXT"
                    elif is_mysql:
                        sql = f"ALTER TABLE ai_context ADD COLUMN {field_name} LONGTEXT"
                    elif is_postgres:
                        sql = f"ALTER TABLE ai_context ADD COLUMN {field_name} TEXT"
                    else:
                        # Fallback to generic TEXT
                        sql = f"ALTER TABLE ai_context ADD COLUMN {field_name} TEXT"
                    
                    try:
                        conn.execute(text(sql))
                        conn.commit()
                        print(f"✅ Added column '{field_name}' ({description})")
                    except Exception as e:
                        print(f"⚠️  Could not add column '{field_name}': {e}")
                        conn.rollback()
            
            print("\n" + "=" * 70)
            print("✅ Migration completed successfully!")
            print("=" * 70)
            print("\nNew Features:")
            print("  • Email Response Rules: Configure AI instructions for email interactions")
            print("  • WhatsApp Response Rules: Configure AI instructions for WhatsApp messages")
            print("  • Parent App Description: Help AI understand your application structure")
            print("\nNext Steps:")
            print("  1. Restart your backend service")
            print("  2. Go to Settings > AI Context to configure the new fields")
            print("  3. Save your settings to apply the rules")
            return True
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
