#!/usr/bin/env python3
"""
Migration: Add per-contact auto-reply settings to authorized_contacts table.

This adds:
- auto_reply_enabled (boolean) - Enable auto-reply for this contact
- auto_reply_mode (string) - 'draft' or 'send'
- auto_reply_ai_instructions (text) - Custom AI instructions per contact
"""

import sqlite3
import sys
from pathlib import Path

def get_db_path():
    """Get the database path."""
    backend_dir = Path(__file__).parent
    instance_dir = backend_dir / 'instance'
    db_path = instance_dir / 'brainr.db'
    return str(db_path)

def migrate_up():
    """Apply migration: Add auto-reply columns to authorized_contacts."""
    db_path = get_db_path()
    
    if not Path(db_path).exists():
        print(f"❌ Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(authorized_contacts)")
        columns = {row[1] for row in cursor.fetchall()}
        
        changes_made = False
        
        # Add auto_reply_enabled if not exists
        if 'auto_reply_enabled' not in columns:
            cursor.execute("""
                ALTER TABLE authorized_contacts 
                ADD COLUMN auto_reply_enabled BOOLEAN DEFAULT 0
            """)
            print("✓ Added auto_reply_enabled column")
            changes_made = True
        
        # Add auto_reply_mode if not exists
        if 'auto_reply_mode' not in columns:
            cursor.execute("""
                ALTER TABLE authorized_contacts 
                ADD COLUMN auto_reply_mode TEXT DEFAULT 'draft'
            """)
            print("✓ Added auto_reply_mode column")
            changes_made = True
        
        # Add auto_reply_ai_instructions if not exists
        if 'auto_reply_ai_instructions' not in columns:
            cursor.execute("""
                ALTER TABLE authorized_contacts 
                ADD COLUMN auto_reply_ai_instructions TEXT
            """)
            print("✓ Added auto_reply_ai_instructions column")
            changes_made = True
        
        if changes_made:
            conn.commit()
            print("✅ Migration completed successfully")
            return True
        else:
            print("ℹ️  No changes needed - columns already exist")
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    finally:
        conn.close()

def migrate_down():
    """Rollback migration: Remove auto-reply columns from authorized_contacts."""
    db_path = get_db_path()
    
    if not Path(db_path).exists():
        print(f"❌ Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # SQLite doesn't support DROP COLUMN easily, so we'll document this
        print("⚠️  SQLite doesn't support dropping columns directly.")
        print("If you need to rollback, you may need to:")
        print("1. Backup the database")
        print("2. Export data")
        print("3. Recreate the table without these columns")
        print("4. Re-import data")
        
        return False
            
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'down':
        success = migrate_down()
    else:
        success = migrate_up()
    
    sys.exit(0 if success else 1)
