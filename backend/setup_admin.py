#!/usr/bin/env python
"""Direct setup script to configure admin credentials."""
import sys
import os

# Set UTF-8 encoding for logging
os.environ['PYTHONIOENCODING'] = 'utf-8'

from app import create_app
from app.extensions import db
from app.models import User, Role, UserRole
from app.auth import hash_password

app = create_app()

with app.app_context():
    ADMIN_USERNAME = "admin@brainr.com"
    ADMIN_EMAIL = "admin@brainr.com"
    ADMIN_PASSWORD = "@@AdminBrainer22"
    
    print(f"Setting up admin credentials...")
    print(f"  Email: {ADMIN_EMAIL}")
    print(f"  Password: {'*' * len(ADMIN_PASSWORD)}")
    
    # Ensure Admin role exists
    admin_role = Role.query.filter_by(name="Admin").first()
    if not admin_role:
        admin_role = Role(name="Admin", description="Full access", is_admin=True, is_system_role=True)
        db.session.add(admin_role)
        db.session.flush()
        print("✓ Created Admin role")
    
    # Check for existing admin user by email
    admin_user = User.query.filter_by(email=ADMIN_EMAIL).first()
    
    if not admin_user:
        # Try to find by username
        admin_user = User.query.filter_by(username=ADMIN_USERNAME).first()
        if admin_user:
            # Update email to correct one
            admin_user.email = ADMIN_EMAIL
            print(f"⚠ Updated admin email to: {ADMIN_EMAIL}")
    
    if admin_user:
        print(f"✓ Admin user exists (ID: {admin_user.id})")
        print(f"   Username: {admin_user.username}")
        print(f"   Email: {admin_user.email}")
        print(f"   Active: {admin_user.is_active}")
        print(f"   Roles: {[r.name for r in admin_user.roles()]}")
        
        # Ensure admin user is active
        if not admin_user.is_active:
            admin_user.is_active = True
            print("   ⚠ Activated admin user")
        
        # Ensure admin user has Admin role
        has_admin_role = any(r.is_admin for r in admin_user.roles())
        if not has_admin_role:
            db.session.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))
            print("   ⚠ Added Admin role to user")
        
        # Reset password
        admin_user.password_hash = hash_password(ADMIN_PASSWORD)
        print(f"   ✓ Password updated")
    else:
        # Create new admin user
        admin_user = User(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD),
            first_name="Admin",
            is_active=True,
        )
        db.session.add(admin_user)
        db.session.flush()
        db.session.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))
        print("✓ Created new admin user")
        print(f"   Username: {ADMIN_USERNAME}")
        print(f"   Email: {ADMIN_EMAIL}")
        print(f"   Password set successfully")
    
    db.session.commit()
    
    print("\n" + "="*60)
    print("SUCCESS: Admin credentials have been set!")
    print("="*60)
    print(f"Login credentials:")
    print(f"  Email/Username: {ADMIN_EMAIL}")
    print(f"  Password: {ADMIN_PASSWORD}")
    print("="*60)
