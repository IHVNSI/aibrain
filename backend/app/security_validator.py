"""SQL Command validation and authorization for remote email/SMS execution."""
import re
import logging
from typing import Tuple, Optional
from backend.app.models import AuthorizedContact

logger = logging.getLogger(__name__)


class CommandAuthorization:
    """Validates SQL commands based on contact authorization level."""
    
    # Command patterns by category
    SELECT_COMMANDS = {
        'SELECT', 'SHOW', 'DESCRIBE', 'DESC', 'EXPLAIN', 'WITH'
    }
    
    WRITE_COMMANDS = {
        'INSERT', 'UPDATE', 'DELETE', 'REPLACE', 'CREATE', 
        'ALTER', 'DROP', 'TRUNCATE', 'GRANT', 'REVOKE'
    }
    
    DANGEROUS_COMMANDS = {
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'REVOKE'
    }
    
    @staticmethod
    def extract_command_type(sql: str) -> Optional[str]:
        """Extract the primary command type from SQL query."""
        # Remove leading whitespace and comments
        sql = sql.strip()
        sql = re.sub(r'^\s*--.*?\n', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'^\s*/\*.*?\*/', '', sql, flags=re.DOTALL)
        sql = sql.strip()
        
        # Get first word
        match = re.match(r'^\s*(\w+)', sql, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return None
    
    @staticmethod
    def is_select_command(sql: str) -> bool:
        """Check if SQL is a SELECT-only command."""
        command = CommandAuthorization.extract_command_type(sql)
        return command in CommandAuthorization.SELECT_COMMANDS
    
    @staticmethod
    def is_write_command(sql: str) -> bool:
        """Check if SQL is a write command (INSERT, UPDATE, DELETE, etc.)."""
        command = CommandAuthorization.extract_command_type(sql)
        return command in CommandAuthorization.WRITE_COMMANDS
    
    @staticmethod
    def is_dangerous_command(sql: str) -> bool:
        """Check if SQL is a dangerous command (DROP, TRUNCATE, etc.)."""
        command = CommandAuthorization.extract_command_type(sql)
        return command in CommandAuthorization.DANGEROUS_COMMANDS
    
    @staticmethod
    def validate_for_contact(
        sql: str,
        sender_email_or_phone: str,
        allow_select_only: bool = True
    ) -> Tuple[bool, str]:
        """
        Validate SQL command against contact authorization level.
        
        Args:
            sql: SQL command to validate
            sender_email_or_phone: Email or phone number of sender
            allow_select_only: If True, restrict to SELECT commands unless authorized
        
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Get contact's permission level
            permission_level = AuthorizedContact.get_permission_level(sender_email_or_phone)
            
            if not permission_level:
                return (False, f"❌ Contact '{sender_email_or_phone}' is not authorized to execute commands")
            
            command = CommandAuthorization.extract_command_type(sql)
            
            if not command:
                return (False, "❌ Could not determine SQL command type")
            
            # Check if dangerous command
            if CommandAuthorization.is_dangerous_command(sql):
                if permission_level != 'ADMIN':
                    return (False, f"❌ Contact with permission level '{permission_level}' cannot execute {command} commands. Only ADMIN can execute dangerous commands.")
            
            # Check if write command
            elif CommandAuthorization.is_write_command(sql):
                if permission_level == 'SELECT_ONLY':
                    return (False, f"❌ Contact with permission level 'SELECT_ONLY' can only execute SELECT queries, not {command}")
                elif permission_level != 'READ_WRITE' and permission_level != 'ADMIN':
                    return (False, f"❌ Contact does not have write permission for {command} command")
            
            # Check if select command
            elif CommandAuthorization.is_select_command(sql):
                # SELECT commands allowed for all permission levels
                pass
            
            else:
                return (False, f"❌ Command type '{command}' is not recognized or allowed")
            
            logger.info(f"✅ SQL command '{command}' authorized for {sender_email_or_phone} (Permission: {permission_level})")
            return (True, f"✅ Command authorized for contact (Permission: {permission_level})")
        
        except Exception as e:
            logger.error(f"Error validating command authorization: {e}")
            return (False, f"❌ Error validating authorization: {str(e)}")


def authorize_command_for_email(sql: str, sender_email: str) -> Tuple[bool, str]:
    """
    Quick validation function for email-originated SQL commands.
    
    By default, only SELECT commands allowed unless sender is authorized.
    """
    # Check if it's a SELECT command
    if CommandAuthorization.is_select_command(sql):
        # SELECT allowed for everyone by default
        return (True, "✅ SELECT command authorized")
    
    # Non-SELECT commands require authorization
    return CommandAuthorization.validate_for_contact(sql, sender_email, allow_select_only=True)


def authorize_command_for_phone(sql: str, sender_phone: str) -> Tuple[bool, str]:
    """
    Quick validation function for SMS/phone-originated SQL commands.
    
    Same rules as email but for phone numbers.
    """
    return authorize_command_for_email(sql, sender_phone)
