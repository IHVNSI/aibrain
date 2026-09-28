#!/usr/bin/env python3
"""
Check database setup and run migration
"""

import sqlite3
import os
from pathlib import Path

def check_database():
    """Check which database has the authorized_contacts table"""
    db_files = [
        'instance/app.db',
        'instance/brainr.db',
        'instance/inventory.db'
    ]
    
    for db_file in db_files:
        if os.path.exists(db_file):
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='authorized_contacts'")
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    print(f"✓ Found authorized_contacts table in: {db_file}")
                    return db_file
                else:
                    print(f"- No authorized_contacts table in: {db_file}")
            except Exception as e:
                print(f"- Error checking {db_file}: {e}")
    
    return None

if __name__ == '__main__':
    db = check_database()
    if db:
        print(f"\nTarget database: {db}")
        # Run migration on this database
        from migrate_auto_reply_per_contact import get_db_path, migrate_up
        
        # Override the database path
        import migrate_auto_reply_per_contact as migration
        original_get_db_path = migration.get_db_path
        migration.get_db_path = lambda: db
        
        migrate_up()
    else:
        print("❌ authorized_contacts table not found in any database")
