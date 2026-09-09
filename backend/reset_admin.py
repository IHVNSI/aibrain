#!/usr/bin/env python
"""Utility script to verify/reset admin credentials."""
import sys
from app import create_app
from app.extensions import db
from app.models import User, Role, UserRole
from app.auth import hash_password

app = create_app()

with app.app_context():
    ADMIN_USERNAME = "admin"
    ADMIN_EMAIL = input("Enter admin email (default: admin@example.com): ").strip() or "admin@example.com"
    ADMIN_PASSWORD = input("Enter admin password (will not be shown): ").strip()
    
    if not ADMIN_PASSWORD:
        print("Error: Password is required")
        sys.exit(1)
    
    # Ensure Admin role exists
    admin_role = Role.query.filter_by(name="Admin").first()
    if not admin_role:
        admin_role = Role(name="Admin", description="Full access", is_admin=True, is_system_role=True)
        db.session.add(admin_role)
        db.session.flush()
        print("✅ Created Admin role")
    
    # Check for existing admin user by email first, then by username
    admin_user = User.query.filter_by(email=ADMIN_EMAIL).first()
    
    if not admin_user:
        # Try to find by username
        admin_user = User.query.filter_by(username=ADMIN_USERNAME).first()
        if admin_user:
            # Update email to correct one
            admin_user.email = ADMIN_EMAIL
            print(f"⚠️  Updated admin email to: {ADMIN_EMAIL}")
    
    if admin_user:
        print(f"✅ Admin user exists (ID: {admin_user.id})")
        print(f"   Username: {admin_user.username}")
        print(f"   Email: {admin_user.email}")
        print(f"   Active: {admin_user.is_active}")
        print(f"   Roles: {[r.name for r in admin_user.roles()]}")
        
        # Ensure admin user is active
        if not admin_user.is_active:
            admin_user.is_active = True
            print("   ⚠️ Activated admin user")
        
        # Ensure admin user has Admin role
        has_admin_role = any(r.is_admin for r in admin_user.roles())
        if not has_admin_role:
            db.session.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))
            print("   ⚠️ Added Admin role to user")
        
        # Reset password
        admin_user.password_hash = hash_password(ADMIN_PASSWORD)
        print(f"   🔐 Reset password to: {ADMIN_PASSWORD}")
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
        print("✅ Created new admin user")
        print(f"   Username: {ADMIN_USERNAME}")
        print(f"   Email: {ADMIN_EMAIL}")
        print(f"   Password: {ADMIN_PASSWORD}")
    
    db.session.commit()
    
    print("\n✅ Admin credentials verified and ready!")
    print(f"\n📝 Login credentials:")
    print(f"   Email/Username: {ADMIN_EMAIL}")
    print(f"   Password: {ADMIN_PASSWORD}")
    print(f"\n⚠️  Please change this password after first login!")
