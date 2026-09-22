"""Email service for reading and responding to emails."""
import os
import logging
from imap_tools import MailBox, AND
from email_validator import validate_email, EmailNotValidError
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class EmailService:
    """Service for reading and managing emails via IMAP."""
    
    def __init__(self, imap_server: str, email: str, password: str, imap_port: int = 993):
        """
        Initialize email service.
        
        Args:
            imap_server: IMAP server address (e.g., 'imap.gmail.com')
            email: Email address
            password: Email password or app-specific password (for Gmail)
            imap_port: IMAP server port (default: 993 for SSL)
        """
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.email = email
        self.password = password
        self.mailbox = None
    
    def connect(self) -> bool:
        """Connect to email server."""
        try:
            self.mailbox = MailBox(self.imap_server, port=self.imap_port)
            self.mailbox.login(self.email, self.password)
            logger.info("Connected to email: %s", self.email)
            return True
        except Exception as e:
            logger.error("Failed to connect to email server: %s", str(e))
            return False
    
    def disconnect(self):
        """Disconnect from email server."""
        if self.mailbox:
            try:
                self.mailbox.logout()
                logger.info("Disconnected from email server")
            except Exception as e:
                logger.warning("Error disconnecting: %s", str(e))
    def get_unread_emails(self, limit: int = 10, folder: str = 'INBOX') -> List[Dict[str, Any]]:
        """
        Get unread emails.
        
        Args:
            limit: Max number of emails to retrieve
            folder: Email folder (default: INBOX)
        
        Returns:
            List of email dictionaries with from, subject, text, html, date
        """
        if not self.mailbox:
            return []
        
        try:
            emails = []
            # Get unread emails, ordered by newest first
            criteria = AND(seen=False)
            
            # Select the folder and fetch emails
            self.mailbox.folder.set(folder)
            for msg in self.mailbox.fetch(criteria, limit=limit, reverse=True):
                emails.append({
                    'id': msg.uid,
                    'from': msg.from_,
                    'to': msg.to,
                    'subject': msg.subject,
                    'text': msg.text or '',
                    'html': msg.html or '',
                    'date': msg.date.isoformat() if msg.date else None,
                    'is_unread': '\\Seen' not in msg.flags,
                    'cc': msg.cc,
                    'bcc': msg.bcc,
                })
            
            logger.info("Retrieved %d unread emails from %s", len(emails), folder)
            return emails
        except Exception as e:
            logger.error("Error retrieving emails from %s: %s", folder, str(e))
            return []
    
    def get_emails_by_date_range(self, days_back: int = 7, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get emails from the last N days.
        
        Args:
            days_back: Number of days to look back
            limit: Max number of emails to retrieve
        
        Returns:
            List of email dictionaries
        """
        if not self.mailbox:
            return []
        
        try:
            # Convert datetime to date for imap_tools compatibility
            since_date = (datetime.now() - timedelta(days=days_back)).date()
            criteria = AND(date_gte=since_date)
            
            emails = []
            # Select INBOX folder
            self.mailbox.folder.set('INBOX')
            for msg in self.mailbox.fetch(criteria, limit=limit, reverse=True):
                emails.append({
                    'id': msg.uid,
                    'from': msg.from_,
                    'subject': msg.subject,
                    'text': msg.text or '',
                    'date': msg.date.isoformat() if msg.date else None,
                    'is_unread': '\\Seen' not in msg.flags,
                })
            
            logger.info("Retrieved %d emails from last %d days", len(emails), days_back)
            return emails
        except Exception as e:
            logger.error("Error retrieving emails by date: %s", str(e))
            return []
    
    def mark_as_read(self, email_id: str, folder: str = 'INBOX') -> bool:
        """Mark email as read."""
        if not self.mailbox:
            return False
        
        try:
            self.mailbox.folder.set(folder)
            self.mailbox.flag([email_id], [r'\Seen'], True)
            logger.info("Marked email %s as read", email_id)
            return True
        except Exception as e:
            logger.error("Error marking email as read: %s", str(e))
            return False
    
    def mark_as_unread(self, email_id: str, folder: str = 'INBOX') -> bool:
        """Mark email as unread."""
        if not self.mailbox:
            return False
        
        try:
            self.mailbox.folder.set(folder)
            self.mailbox.flag([email_id], [r'\Seen'], False)
            logger.info("Marked email %s as unread", email_id)
            return True
        except Exception as e:
            logger.error("Error marking email as unread: %s", str(e))
            return False
    
    def search_emails(self, query: str, limit: int = 10, folder: str = 'INBOX') -> List[Dict[str, Any]]:
        """
        Search emails by subject or content.
        
        Args:
            query: Search query (e.g., 'report', 'invoice')
            limit: Max number of results
            folder: Email folder (default: INBOX)
        
        Returns:
            List of matching emails
        """
        if not self.mailbox:
            return []
        
        try:
            criteria = AND(subject=query)
            
            emails = []
            self.mailbox.folder.set(folder)
            for msg in self.mailbox.fetch(criteria, limit=limit):
                if query.lower() in msg.subject.lower() or query.lower() in (msg.text or '').lower():
                    emails.append({
                        'id': msg.uid,
                        'from': msg.from_,
                        'subject': msg.subject,
                        'text': msg.text or '',
                        'date': msg.date.isoformat() if msg.date else None,
                    })
            
            return emails
        except Exception as e:
            logger.error("Error searching emails: %s", str(e))
            return []
    
    def get_folder_list(self) -> List[str]:
        """Get list of available folders."""
        if not self.mailbox:
            return []
        
        try:
            folders = self.mailbox.folder.list()
            return [f.name for f in folders]
        except Exception as e:
            logger.error("Error getting folder list: %s", str(e))
            return []


class EmailConfig:
    """Email configuration from environment variables."""
    
    # IMAP server configurations (common providers)
    IMAP_SERVERS = {
        'gmail': 'imap.gmail.com',
        'outlook': 'outlook.office365.com',
        'yahoo': 'imap.mail.yahoo.com',
        'icloud': 'imap.mail.me.com',
        'custom': os.getenv('EMAIL_IMAP_SERVER', ''),
    }
    
    @classmethod
    def get_email_service(cls, provider: str = 'gmail') -> Optional[EmailService]:
        """
        Get email service for configured provider.
        
        Environment variables needed:
        - EMAIL_ADDRESS: Email address
        - EMAIL_PASSWORD: Email password or app-specific password
        - EMAIL_PROVIDER: Email provider (gmail, outlook, etc.)
        
        For Gmail:
        - Use app-specific password (not regular password)
        - Enable "Less secure app access" if using regular password
        
        Args:
            provider: Email provider type
        
        Returns:
            EmailService instance or None if not configured
        """
        email_address = os.getenv('EMAIL_ADDRESS')
        email_password = os.getenv('EMAIL_PASSWORD')
        provider = os.getenv('EMAIL_PROVIDER', provider)
        
        if not email_address or not email_password:
            logger.warning("EMAIL_ADDRESS or EMAIL_PASSWORD not configured in .env")
            return None
        
        imap_server = cls.IMAP_SERVERS.get(provider.lower(), os.getenv('EMAIL_IMAP_SERVER'))
        
        if not imap_server:
            logger.error("Unknown email provider: %s", provider)
            return None
        
        # Get IMAP port from .env, default to 993 for SSL
        try:
            imap_port = int(os.getenv('EMAIL_IMAP_PORT', '993'))
        except ValueError:
            imap_port = 993
        
        service = EmailService(imap_server, email_address, email_password, imap_port)
        
        # Test connection
        if service.connect():
            return service
        else:
            return None
