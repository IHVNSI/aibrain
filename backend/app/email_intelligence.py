"""
Email intelligence: sender detection, auto-response generation, and draft management.

Provides:
- Sender type detection (client, employee, internal, vendor, etc.)
- Auto-response generation based on email content
- Draft email creation for manual review
"""
import logging
import re
from datetime import datetime
from typing import Dict, Tuple, Optional, List

from .extensions import db
from .models import StoredEmail, DraftEmail
from .llm.factory import build_llm

logger = logging.getLogger(__name__)


class SenderDetector:
    """Detect sender type from email address, subject, and body."""
    
    @staticmethod
    def detect_sender_type(from_address: str, subject: str = "", body: str = "") -> str:
        """
        Detect sender type from email properties.
        
        Returns one of:
        - 'client': Customer/business partner (from contacts table)
        - 'employee': Internal team member (from staff/employee list)
        - 'vendor': External vendor/supplier
        - 'admin': System/administration email
        - 'support': Support/system notification
        - 'unknown': Unable to determine
        """
        if not from_address:
            return 'unknown'
        
        from_lower = from_address.lower()
        
        # Check if internal email (common internal domain patterns)
        internal_patterns = [
            r'@(brainr\.com|company\.com|internal\.)',
            r'(noreply|admin|system|support)',
        ]
        for pattern in internal_patterns:
            if re.search(pattern, from_lower):
                return 'admin'
        
        # Check if support/notification
        support_patterns = [
            r'(support|help|notification|alert|system)',
            r'@(gmail\.com|hotmail\.com|yahoo\.com).*support',
        ]
        for pattern in support_patterns:
            if re.search(pattern, subject.lower() + ' ' + body.lower()):
                return 'support'
        
        # Check if existing client
        try:
            # Try to lookup in database contacts (if using source DB)
            # For now, just use pattern matching
            pass
        except Exception as e:
            logger.debug(f"Could not check contacts: {e}")
        
        # Vendor patterns
        vendor_patterns = [
            r'(invoice|quote|delivery|order|shipment|tracking)',
            r'(supplier|vendor|manufacturer|distributor)',
        ]
        for pattern in vendor_patterns:
            if re.search(pattern, subject.lower() + ' ' + body.lower()):
                return 'vendor'
        
        # Default to client (likely incoming business inquiry)
        return 'client'
    
    @staticmethod
    def extract_sender_info(from_address: str) -> Dict[str, str]:
        """Extract sender name and email from 'Name <email@domain.com>' format."""
        # Parse "Name <email@domain.com>" or just "email@domain.com"
        match = re.match(r'^(.+?)\s*<(.+?)>$', from_address)
        if match:
            return {
                'name': match.group(1).strip(),
                'email': match.group(2).strip()
            }
        return {
            'name': from_address.split('@')[0] if '@' in from_address else from_address,
            'email': from_address
        }


class AutoResponseGenerator:
    """Generate appropriate auto-responses based on email content and sender type."""
    
    @staticmethod
    def generate_response(
        email: StoredEmail,
        sender_type: str,
        auto_reply_settings: Optional[Dict] = None,
        llm = None
    ) -> Optional[str]:
        """
        Generate an appropriate auto-response.
        
        Returns: Response text or None if no response should be generated
        """
        # Generate responses even if settings aren't configured (for drafts)
        # Only skip if settings explicitly disabled
        if auto_reply_settings and not auto_reply_settings.get('enabled'):
            return None
        
        sender_info = SenderDetector.extract_sender_info(email.from_address)
        sender_name = sender_info.get('name', 'there')
        
        # Template-based responses for common scenarios
        subject_lower = (email.subject or '').lower()
        body_lower = (email.body or '').lower()
        
        # Check email intent
        if any(word in subject_lower or word in body_lower for word in ['invoice', 'payment', 'bill']):
            return f"""Hello {sender_name},

Thank you for your email. We have received your message regarding the invoice/payment.

Our team will review your inquiry and get back to you shortly.

Best regards,
BrainR Team"""
        
        if any(word in subject_lower or word in body_lower for word in ['quote', 'estimate', 'proposal']):
            return f"""Hello {sender_name},

Thank you for your interest! We've received your request for a quote.

Our team will prepare a detailed estimate and send it to you within 24 hours.

We appreciate your business!

Best regards,
BrainR Team"""
        
        if any(word in subject_lower or word in body_lower for word in ['support', 'help', 'issue', 'problem', 'urgent']):
            return f"""Hello {sender_name},

Thank you for reaching out. We've received your support request and have prioritized it.

Our support team will investigate and respond with a solution shortly.

We appreciate your patience.

Best regards,
Support Team"""
        
        # Use LLM to generate contextual response if configured
        if auto_reply_settings.get('use_llm') and llm:
            try:
                prompt = f"""Generate a professional auto-response email to the following email:

From: {email.from_address}
Subject: {email.subject}
Body: {email.body[:500]}  # First 500 chars

Sender Type: {sender_type}

The response should:
- Be professional and concise
- Acknowledge receipt of the email
- Provide next steps or timeline
- Be 2-3 sentences max

Generate ONLY the response body, no subject line."""
                
                response = llm.chat([
                    {"role": "system", "content": "You are a helpful email assistant that generates professional auto-responses."},
                    {"role": "user", "content": prompt}
                ])
                return response if response else None
            except Exception as e:
                logger.warning(f"Failed to generate LLM response: {e}")
        
        # Default generic response
        return f"""Hello {sender_name},

Thank you for your email. We have received your message and will respond shortly.

Best regards,
BrainR Team"""
    
    @staticmethod
    def should_respond(sender_type: str, auto_reply_settings: Optional[Dict]) -> bool:
        """Determine if we should send an auto-response based on sender type.
        
        Default behavior: Always respond (create drafts) unless explicitly disabled.
        Responders exclude admin/support emails by default.
        """
        # Default: respond to all except system emails
        if not auto_reply_settings:
            return sender_type not in ['admin', 'support', 'unknown']
        
        if not auto_reply_settings.get('enabled'):
            return False
        
        # Check blacklist
        excluded_types = auto_reply_settings.get('exclude_sender_types', [])
        if sender_type in excluded_types:
            return False
        
        # Check if this sender type should get a response
        enabled_types = auto_reply_settings.get('enabled_for_sender_types', ['client', 'vendor'])
        return sender_type in enabled_types


class EmailDraftManager:
    """Manage draft email creation for manual review before sending."""
    
    @staticmethod
    def create_draft_response(
        email: StoredEmail,
        response_body: str,
        sender_type: str,
        notes: str = ""
    ) -> Optional[DraftEmail]:
        """
        Create a draft response email for manual review.
        
        Returns: DraftEmail instance or None if failed
        """
        try:
            sender_info = SenderDetector.extract_sender_info(email.from_address)
            recipient_email = sender_info.get('email', email.from_address)
            
            # Generate subject (Re: original subject)
            subject = email.subject or 'Response'
            if not subject.startswith('Re:'):
                subject = f"Re: {subject}"
            
            draft = DraftEmail(
                to_address=recipient_email,
                subject=subject,
                body=response_body,
                html_body=f"<p>{response_body.replace(chr(10), '<br>')}</p>",
                status='draft'  # Only use fields that definitely exist
            )
            
            db.session.add(draft)
            db.session.commit()
            
            logger.info(f"Created draft response for email {email.id} from {email.from_address}")
            return draft
        
        except Exception as e:
            logger.error(f"Failed to create draft response: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def get_pending_drafts(sender_type: Optional[str] = None) -> List[DraftEmail]:
        """Get all pending draft responses."""
        try:
            query = DraftEmail.query.filter_by(status='draft')
            return query.all()
        except Exception as e:
            logger.error(f"Error getting pending drafts: {e}")
            return []


class EmailProcessor:
    """Main processor for handling incoming emails with intelligence."""
    
    @staticmethod
    def process_incoming_email(
        email: StoredEmail,
        auto_reply_settings: Optional[Dict] = None,
        use_drafts: bool = True
    ) -> Dict[str, any]:
        """
        Process an incoming email: detect sender, generate response, create draft if needed.
        
        Returns:
        {
            'email_id': int,
            'sender_type': str,
            'should_respond': bool,
            'response_generated': bool,
            'draft_created': bool,
            'draft_id': int or None,
            'auto_sent': bool,
            'status': str
        }
        """
        result = {
            'email_id': email.id,
            'sender_type': 'unknown',
            'should_respond': False,
            'response_generated': False,
            'draft_created': False,
            'draft_id': None,
            'auto_sent': False,
            'status': 'processed'
        }
        
        try:
            # Step 1: Detect sender type
            sender_type = SenderDetector.detect_sender_type(
                email.from_address,
                email.subject or "",
                email.body or ""
            )
            result['sender_type'] = sender_type
            
            # Step 2: Check if we should respond
            should_respond = AutoResponseGenerator.should_respond(sender_type, auto_reply_settings)
            result['should_respond'] = should_respond
            
            if not should_respond:
                logger.info(f"No auto-response configured for sender type: {sender_type}")
                return result
            
            # Step 3: Generate response
            llm = build_llm() if auto_reply_settings.get('use_llm') else None
            response_body = AutoResponseGenerator.generate_response(
                email,
                sender_type,
                auto_reply_settings,
                llm
            )
            
            if not response_body:
                logger.info(f"No response generated for email {email.id}")
                return result
            
            result['response_generated'] = True
            
            # Step 4: Create draft or send
            # Default behavior: create drafts for review if no auto_reply_settings
            auto_send = auto_reply_settings.get('auto_send', False) if auto_reply_settings else False
            
            if use_drafts and not auto_send:
                # Create draft for manual review
                draft = EmailDraftManager.create_draft_response(
                    email,
                    response_body,
                    sender_type,
                    notes=f"Auto-reply (pending review) for {sender_type}"
                )
                
                if draft:
                    result['draft_created'] = True
                    result['draft_id'] = draft.id
                    logger.info(f"Draft created (ID: {draft.id}) for review")
            else:
                # Auto-send if configured
                try:
                    from .api.email_scheduling import send_email_smtp
                    
                    sender_info = SenderDetector.extract_sender_info(email.from_address)
                    recipient_email = sender_info.get('email', email.from_address)
                    
                    subject = email.subject or 'Response'
                    if not subject.startswith('Re:'):
                        subject = f"Re: {subject}"
                    
                    success, error_msg = send_email_smtp(
                        recipient_email,
                        subject,
                        response_body
                    )
                    
                    if success:
                        result['auto_sent'] = True
                        logger.info(f"Auto-response sent to {recipient_email}")
                    else:
                        result['status'] = 'auto_send_failed'
                        logger.warning(f"Failed to auto-send response: {error_msg}")
                        
                        # Fall back to draft
                        draft = EmailDraftManager.create_draft_response(
                            email,
                            response_body,
                            sender_type,
                            notes=f"Auto-reply (send failed): {error_msg}"
                        )
                        if draft:
                            result['draft_created'] = True
                            result['draft_id'] = draft.id
                
                except Exception as e:
                    logger.error(f"Error in auto-send: {e}")
                    result['status'] = 'auto_send_error'
        
        except Exception as e:
            logger.error(f"Error processing email {email.id}: {e}")
            result['status'] = 'processing_error'
        
        return result
