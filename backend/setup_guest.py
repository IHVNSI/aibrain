#!/usr/bin/env python
"""Setup guest user account."""
import sys
import os

os.environ['PYTHONIOENCODING'] = 'utf-8'

from app import create_app
from app.extensions import db
from app.models import User, Role, UserRole
from app.auth import hash_password

app = create_app()

with app.app_context():
    guest = User.query.filter_by(email='guest@guest.com').first()
    if guest:
        print(f'✓ Guest user exists (ID: {guest.id})')
        print(f'  Email: {guest.email}')
        print(f'  Username: {guest.username}')
        print(f'  Active: {guest.is_active}')
        # Ensure password is correct
        guest.password_hash = hash_password('Guest123')
        db.session.commit()
        print(f'  ✓ Password updated to: Guest123')
    else:
        print('Creating guest user...')
        guest = User(
            username='guest',
            email='guest@guest.com',
            password_hash=hash_password('Guest123'),
            first_name='Guest',
            is_active=True
        )
        db.session.add(guest)
        db.session.flush()
        user_role = Role.query.filter_by(name='User').first()
        if user_role:
            db.session.add(UserRole(user_id=guest.id, role_id=user_role.id))
        db.session.commit()
        print('✓ Guest user created successfully')
        print(f'  Email: guest@guest.com')
        print(f'  Password: Guest123')

    print("\n" + "="*60)
    print("LOGIN CREDENTIALS")
    print("="*60)
    print("Admin Account:")
    print("  Email: admin@brainr.com")
    print("  Password: @@AdminBrainer22")
    print("\nGuest Account:")
    print("  Email: guest@guest.com")
    print("  Password: Guest123")
    print("="*60)
