#!/usr/bin/env python
"""Reset admin password for testing purposes."""

from app import create_app
from app.extensions import db
from app.models import User
from app.auth import hash_password

# Initialize app
app = create_app()

with app.app_context():
    # Try to find and update admin user
    admin = User.query.filter_by(username='admin').first()
    if admin:
        admin.password_hash = hash_password('admin123')
        db.session.commit()
        print("✓ Admin password set to 'admin123'")
    else:
        print("✗ Admin user not found")
