#!/usr/bin/env python
"""Verify login users are set up."""
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from app import create_app
from app.models import User

app = create_app()

with app.app_context():
    admin = User.query.filter_by(email='admin@brainr.com').first()
    guest = User.query.filter_by(email='guest@guest.com').first()
    
    print("\n" + "="*60)
    print("LOGIN USERS STATUS")
    print("="*60)
    print(f"Admin (admin@brainr.com):  {'✅ FOUND' if admin else '❌ NOT FOUND'}")
    print(f"Guest (guest@guest.com):   {'✅ FOUND' if guest else '❌ NOT FOUND'}")
    print("="*60)
    
    if admin and guest:
        print("\n✅ LOGIN SYSTEM READY - You can now login!")
        print("\nCredentials:")
        print("  Admin: admin@brainr.com / @@AdminBrainer22")
        print("  Guest: guest@guest.com / Guest123")
    else:
        print("\n❌ Some users are missing. Run setup scripts:")
        if not admin:
            print("  python setup_admin.py")
        if not guest:
            print("  python setup_guest.py")
    print("="*60 + "\n")
