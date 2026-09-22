#!/usr/bin/env python
"""Test Gmail email configuration."""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.email_service import EmailService

def test_gmail_config(email_address: str, app_password: str):
    """Test Gmail configuration."""
    print(f"\n🔍 Testing Gmail configuration for: {email_address}")
    print("=" * 60)
    
    # Test parameters
    imap_server = "imap.gmail.com"
    imap_port = 993
    
    print(f"IMAP Server: {imap_server}")
    print(f"IMAP Port: {imap_port}")
    print(f"Email: {email_address}")
    print("-" * 60)
    
    try:
        # Create service
        print("\n📧 Creating EmailService...")
        service = EmailService(imap_server, email_address, app_password, imap_port)
        
        # Test connection
        print("🔐 Attempting to connect to IMAP server...")
        if service.connect():
            print("✅ Connection successful!")
            
            # Try to get inbox info
            try:
                service.mailbox.folder.set('INBOX')
                print("📬 Successfully accessed INBOX")
                service.disconnect()
                print("✅ Test completed successfully!")
                return True
            except Exception as e:
                print(f"❌ Error accessing INBOX: {e}")
                service.disconnect()
                return False
        else:
            print("❌ Connection failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_gmail.py <email> <app_password>")
        print("\nExample:")
        print("  python test_gmail.py user@gmail.com abcd1234efgh5678")
        print("\nNote: For Gmail, use an App Password (not your regular password)")
        print("Generate one at: https://myaccount.google.com/apppasswords")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    success = test_gmail_config(email, password)
    sys.exit(0 if success else 1)
