"""Email service for reading and responding to emails."""
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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
        Get unread emails (with fallback to recent emails if unread returns 0).
        
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
            
            # If no unread emails found, try to get recent emails from last 24 hours instead
            if not emails:
                logger.info(f"No unread emails found in {folder}, fetching recent emails from last 24 hours...")
                self.mailbox.folder.set(folder)
                since_date = (datetime.now() - timedelta(days=1)).date()
                criteria = AND(date_gte=since_date)
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
                logger.info("Retrieved %d recent emails from %s (last 24 hours)", len(emails), folder)
            
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
    
    def get_all_emails(self, folder: str = 'INBOX', limit: int = None) -> List[Dict[str, Any]]:
        """
        Get ALL emails from a folder (for initial bulk download).
        
        Args:
            folder: Email folder (default: INBOX)
            limit: Max number of emails to retrieve (None = unlimited)
        
        Returns:
            List of email dictionaries
        """
        if not self.mailbox:
            return []
        
        try:
            emails = []
            self.mailbox.folder.set(folder)
            
            # Fetch all emails, ordered by oldest first
            if limit:
                for msg in self.mailbox.fetch(limit=limit, reverse=False):
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
            else:
                for msg in self.mailbox.fetch(reverse=False):
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
            
            logger.info("Retrieved %d total emails from %s", len(emails), folder)
            return emails
        except Exception as e:
            logger.error("Error retrieving all emails from %s: %s", folder, str(e))
            return []
    
    def get_emails_after_date(self, after_date: datetime, folder: str = 'INBOX', limit: int = None) -> List[Dict[str, Any]]:
        """
        Get emails received after a specific date (for incremental sync).
        
        Args:
            after_date: Datetime to retrieve emails after
            folder: Email folder (default: INBOX)
            limit: Max number of emails to retrieve (None = unlimited)
        
        Returns:
            List of email dictionaries
        """
        if not self.mailbox:
            return []
        
        try:
            # Convert datetime to date for imap_tools compatibility
            since_date = after_date.date()
            criteria = AND(date_gte=since_date)
            
            emails = []
            self.mailbox.folder.set(folder)
            
            # Fetch emails, ordered by newest first
            if limit:
                for msg in self.mailbox.fetch(criteria, limit=limit, reverse=True):
                    # Filter by time if date precision is needed
                    if msg.date and msg.date > after_date:
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
            else:
                for msg in self.mailbox.fetch(criteria, reverse=True):
                    # Filter by time if date precision is needed
                    if msg.date and msg.date > after_date:
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
            
            logger.info("Retrieved %d emails after %s from %s", len(emails), after_date, folder)
            return emails
        except Exception as e:
            logger.error("Error retrieving emails after date: %s", str(e))
            return []
    
    def get_all_folders_emails(self, limit_per_folder: int = None, include_folders: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all emails from all folders (or specified folders).
        
        Args:
            limit_per_folder: Max emails per folder (None = unlimited)
            include_folders: List of folder names to include (None = all)
        
        Returns:
            Dictionary with folder names as keys and email lists as values
        """
        if not self.mailbox:
            return {}
        
        try:
            result = {}
            folders = self.get_folder_list()
            
            for folder in folders:
                if include_folders and folder not in include_folders:
                    continue
                
                logger.info("Syncing folder: %s", folder)
                emails = self.get_all_emails(folder, limit=limit_per_folder)
                result[folder] = emails
            
            logger.info("Retrieved emails from %d folders", len(result))
            return result
        except Exception as e:
            logger.error("Error retrieving all folder emails: %s", str(e))
            return {}


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
    
    # SMTP server configurations (common providers)
    SMTP_SERVERS = {
        'gmail': ('smtp.gmail.com', 587),
        'outlook': ('smtp-mail.outlook.com', 587),
        'yahoo': ('smtp.mail.yahoo.com', 587),
        'icloud': ('smtp.mail.icloud.com', 587),
        'custom': (os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com'), 
                   int(os.getenv('EMAIL_SMTP_PORT', '587')))
    }
    
    def __init__(self):
        """Initialize email configuration from environment."""
        self.from_address = os.getenv('EMAIL_ADDRESS')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.provider = os.getenv('EMAIL_PROVIDER', 'gmail').lower()
        
        # Get SMTP settings
        smtp_config = self.SMTP_SERVERS.get(self.provider, ('smtp.gmail.com', 587))
        self.smtp_server, self.smtp_port = smtp_config
        
        # Determine SSL/TLS
        self.use_ssl = int(self.smtp_port) == 465
    
    @classmethod
    def get_current(cls) -> Optional['EmailConfig']:
        """
        Get current email configuration.
        
        Returns:
            EmailConfig instance if email is configured, None otherwise
        """
        email_address = os.getenv('EMAIL_ADDRESS')
        email_password = os.getenv('EMAIL_PASSWORD')
        
        if not email_address or not email_password:
            logger.warning("EMAIL_ADDRESS or EMAIL_PASSWORD not configured in .env")
            return None
        
        config = cls()
        return config
    
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


def send_email_via_service(recipient: str, subject: str, body: str, html_body: str = None, 
                          cc_list: List[str] = None, bcc_list: List[str] = None, 
                          config: EmailConfig = None) -> Dict[str, Any]:
    """
    Send email via SMTP using EmailConfig.
    
    Args:
        recipient: Recipient email address
        subject: Email subject
        body: Plain text email body
        html_body: HTML email body (optional)
        cc_list: List of CC recipients (optional)
        bcc_list: List of BCC recipients (optional)
        config: EmailConfig instance (if None, uses current config)
    
    Returns:
        Dictionary with 'success' (bool) and 'error' (str if failed) keys
    """
    try:
        # Get config if not provided
        if not config:
            config = EmailConfig.get_current()
            if not config:
                return {
                    "success": False,
                    "error": "Email configuration not available (missing EMAIL_ADDRESS or EMAIL_PASSWORD)"
                }
        
        # Validate credentials
        if not config.from_address or not config.email_password:
            return {
                "success": False,
                "error": "Email credentials not configured"
            }
        
        # Create MIME message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = config.from_address
        msg['To'] = recipient
        
        # Add CC and BCC
        if cc_list:
            cc_str = ', '.join(cc_list)
            msg['Cc'] = cc_str
        
        if bcc_list:
            bcc_str = ', '.join(bcc_list)
            msg['Bcc'] = bcc_str
        
        # Attach body parts
        msg.attach(MIMEText(body, 'plain'))
        if html_body:
            msg.attach(MIMEText(html_body, 'html'))
        
        # Build recipient list for sending
        recipients = [recipient]
        if cc_list:
            recipients.extend(cc_list)
        if bcc_list:
            recipients.extend(bcc_list)
        
        # Connect and send
        logger.info(f"📧 Connecting to SMTP: {config.smtp_server}:{config.smtp_port} (SSL={config.use_ssl})")
        
        if config.use_ssl:
            server = smtplib.SMTP_SSL(config.smtp_server, int(config.smtp_port), timeout=10)
        else:
            server = smtplib.SMTP(config.smtp_server, int(config.smtp_port), timeout=10)
            server.starttls()
        
        try:
            logger.info(f"🔐 Logging in as {config.from_address}")
            server.login(config.from_address, config.email_password)
            
            logger.info(f"📨 Sending email to {recipient}")
            server.sendmail(config.from_address, recipients, msg.as_string())
            
            logger.info(f"✅ Email sent successfully to {recipient}")
            return {
                "success": True,
                "message": f"Email sent to {recipient}"
            }
        finally:
            server.quit()
    
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"SMTP authentication failed: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }
    except smtplib.SMTPException as e:
        error_msg = f"SMTP error: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }
