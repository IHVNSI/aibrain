"""Improved WhatsApp Web login detection and status tracking."""
import logging
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)


def check_whatsapp_login_status(driver):
    """
    Check if user is logged into WhatsApp Web.
    
    Returns True if:
    - Chat interface is visible (//div[@data-testid='chat'])
    - Chat list is present (conversation list)
    - No login screen visible
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        bool: True if logged in, False otherwise
    """
    if not driver:
        return False
    
    try:
        # Method 1: Check for main chat interface
        try:
            WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, "//div[@data-testid='chat']"))
            )
            logger.debug("✓ Chat interface detected")
            return True
        except:
            pass
        
        # Method 2: Check for chat list (conversations sidebar)
        try:
            WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, "//div[@data-testid='chat-list']"))
            )
            logger.debug("✓ Chat list detected")
            return True
        except:
            pass
        
        # Method 3: Check if any chat element exists
        try:
            elements = driver.find_elements(By.XPATH, "//div[@role='listitem'][@data-testid]")
            if elements and len(elements) > 0:
                logger.debug(f"✓ Found {len(elements)} chat list items")
                return True
        except:
            pass
        
        # Method 4: Check for logout button (only visible when logged in)
        try:
            driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Menu') or contains(@aria-label, 'menu')]")
            logger.debug("✓ Menu button detected (user logged in)")
            return True
        except:
            pass
        
        # Check if QR code screen is still showing (not logged in)
        try:
            driver.find_element(By.XPATH, "//canvas[@aria-label='Scan this QR code']")
            logger.debug("ℹ️  QR code still visible (not logged in)")
            return False
        except:
            pass
        
        logger.debug("ℹ️  Could not determine login status")
        return False
        
    except Exception as e:
        logger.warning(f"Error checking login status: {e}")
        return False


def wait_for_login_completion(driver, timeout=120):
    """
    Wait for login to complete after QR code scan.
    
    Args:
        driver: Selenium WebDriver instance
        timeout: Maximum seconds to wait
        
    Returns:
        bool: True if login detected, False if timeout
    """
    if not driver:
        return False
    
    start_time = time.time()
    last_check = 0
    
    while time.time() - start_time < timeout:
        try:
            # Check every 1 second
            if time.time() - last_check >= 1:
                if check_whatsapp_login_status(driver):
                    logger.info("✓ WhatsApp login detected!")
                    time.sleep(2)  # Wait for full load
                    return True
                last_check = time.time()
            
            time.sleep(0.1)
            
        except Exception as e:
            logger.warning(f"Error waiting for login: {e}")
            time.sleep(1)
    
    logger.warning(f"Login wait timeout ({timeout}s) - QR code may not have been scanned")
    return False


def get_whatsapp_chat_list(driver) -> list:
    """
    Get list of active chats/conversations.
    
    Returns:
        list: Chat names/identifiers
    """
    if not driver:
        return []
    
    try:
        # Find all chat list items
        chat_elements = driver.find_elements(By.XPATH, "//div[@role='listitem']")
        chats = []
        
        for element in chat_elements[:20]:  # Limit to 20 recent chats
            try:
                # Try to get chat name/number
                text = element.text
                if text:
                    chats.append(text)
            except:
                pass
        
        logger.info(f"Found {len(chats)} active chats")
        return chats
        
    except Exception as e:
        logger.warning(f"Error getting chat list: {e}")
        return []


def extract_received_messages(driver, from_chat_name: str = None) -> list:
    """
    Extract recent messages from the chat window.
    
    Args:
        driver: Selenium WebDriver instance
        from_chat_name: Optional - specific chat to check
        
    Returns:
        list: Messages with sender, content, timestamp
    """
    if not driver:
        return []
    
    try:
        messages = []
        
        # Find all message elements in current chat
        message_elements = driver.find_elements(
            By.XPATH, 
            "//div[@data-testid='msg-container']"
        )
        
        for msg_element in message_elements[-20:]:  # Get last 20 messages
            try:
                # Extract message info
                msg_text = msg_element.text
                msg_time = None
                sender = None
                
                # Try to get message time
                try:
                    time_element = msg_element.find_element(By.XPATH, ".//span[@data-testid='msg_time']")
                    msg_time = time_element.get_attribute("data-timestamp")
                except:
                    pass
                
                # Try to get sender info
                try:
                    sender_element = msg_element.find_element(By.XPATH, ".//span[@class='copyable-text']")
                    sender = sender_element.text
                except:
                    pass
                
                if msg_text:
                    messages.append({
                        "text": msg_text,
                        "sender": sender or "unknown",
                        "timestamp": msg_time,
                        "is_received": "web.whatsapp.com" not in str(msg_element.get_attribute("class"))
                    })
            
            except Exception as e:
                logger.debug(f"Error extracting message: {e}")
                continue
        
        return messages
        
    except Exception as e:
        logger.warning(f"Error extracting messages: {e}")
        return []
