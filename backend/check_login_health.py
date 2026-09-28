#!/usr/bin/env python
"""Quick diagnostic script to check login system health."""
import sys
import os

os.environ['PYTHONIOENCODING'] = 'utf-8'

from app import create_app
from app.extensions import db
from app.models import User, AuthConfig

app = create_app()

print("\n" + "="*70)
print("🔐 LOGIN SYSTEM HEALTH CHECK")
print("="*70 + "\n")

with app.app_context():
    # Check admin user
    print("1️⃣  Admin User:")
    admin = User.query.filter_by(email='admin@brainr.com').first()
    if admin:
        print(f"   ✅ Exists (ID: {admin.id})")
        print(f"      Email: {admin.email}")
        print(f"      Username: {admin.username}")
        print(f"      Active: {admin.is_active}")
        print(f"      Roles: {[r.name for r in admin.roles()]}")
    else:
        print("   ❌ Not found - Run: python setup_admin.py")
    
    # Check guest user
    print("\n2️⃣  Guest User:")
    guest = User.query.filter_by(email='guest@guest.com').first()
    if guest:
        print(f"   ✅ Exists (ID: {guest.id})")
        print(f"      Email: {guest.email}")
        print(f"      Username: {guest.username}")
        print(f"      Active: {guest.is_active}")
    else:
        print("   ❌ Not found - Run: python setup_guest.py")
    
    # Check auth config
    print("\n3️⃣  Auth Configuration:")
    auth_config = AuthConfig.query.first()
    if auth_config:
        print(f"   ✅ Found (ID: {auth_config.id})")
        print(f"      Configured: {auth_config.configured}")
        print(f"      Users Table: {auth_config.users_table}")
    else:
        print("   ⚠️  No auth config (using built-in auth)")
    
    # Summary
    print("\n" + "="*70)
    if admin and guest:
        print("✅ LOGIN SYSTEM READY")
        print("\nLogin with:")
        print("  Admin: admin@brainr.com / @@AdminBrainer22")
        print("  Guest: guest@guest.com / Guest123")
    else:
        print("❌ LOGIN SYSTEM NOT READY")
        print("\nRun these to fix:")
        if not admin:
            print("  python setup_admin.py")
        if not guest:
            print("  python setup_guest.py")
    print("="*70 + "\n")
