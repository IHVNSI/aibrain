"""WhatsApp Web automation service - Login via QR code and send/receive messages."""
import logging
import os
import time
import base64
import re
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import pyqrcode
import io

logger = logging.getLogger(__name__)

# Session storage path
SESSION_DIR = Path(__file__).parent.parent.parent / "whatsapp_sessions"
SESSION_DIR.mkdir(exist_ok=True)


class WhatsAppWeb:
    """WhatsApp Web automation using Selenium."""
    
    def __init__(self, session_name="default"):
        """
        Initialize WhatsApp Web driver.
        
        Args:
            session_name: Name of session for storing login data
        """
        self.session_name = session_name
        self.session_path = SESSION_DIR / f"{session_name}_data"
        self.driver = None
        self.is_logged_in = False
        self.qr_code = None
    
    def setup_driver(self):
        """Setup Chrome WebDriver with proper options."""
        try:
            chrome_options = Options()
            
            # Use existing session if available
            if self.session_path.exists():
                chrome_options.add_argument(f"user-data-dir={self.session_path}")
                logger.info(f"Using existing WhatsApp session: {self.session_path}")
            else:
                self.session_path.mkdir(exist_ok=True, parents=True)
                chrome_options.add_argument(f"user-data-dir={self.session_path}")
                logger.info(f"Creating new WhatsApp session: {self.session_path}")
            
            # Additional options for stability
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # For headless (optional - set False to see browser)
            # chrome_options.add_argument("--headless")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            logger.info("✓ Chrome WebDriver initialized")
            return True
        
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {e}")
            return False
    
    def login(self):
        """
        Login to WhatsApp Web via QR code.
        Waits for user to scan QR code on screen.
        """
        try:
            if not self.driver:
                if not self.setup_driver():
                    return False
            
            logger.info("Opening WhatsApp Web...")
            self.driver.get("https://web.whatsapp.com/")
            
            # Check if already logged in
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@data-testid='chat']"))
                )
                logger.info("✓ Already logged in to WhatsApp Web")
                self.is_logged_in = True
                return True
            except:
                pass
            
            # Wait for QR code to appear
            logger.info("Waiting for QR code...")
            qr_element = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//canvas[@aria-label='Scan this QR code to link a device!']"))
            )
            
            # Capture QR code
            self._capture_qr_code()
            logger.info("📱 QR code displayed - Please scan with your WhatsApp phone")
            
            # Wait for user to scan QR code
            logger.info("Waiting for QR code scan (this may take 30-60 seconds)...")
            max_wait = 120  # 2 minutes
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                try:
                    # Check if login was successful
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@data-testid='chat']"))
                    )
                    logger.info("✓ WhatsApp QR code scanned successfully!")
                    self.is_logged_in = True
                    time.sleep(2)  # Wait for full load
                    return True
                except:
                    time.sleep(1)
            
            logger.warning("QR code scan timeout - Please try again")
            return False
        
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    def _capture_qr_code(self):
        """Capture and save QR code image."""
        try:
            qr_canvas = self.driver.find_element(
                By.XPATH, 
                "//canvas[@aria-label='Scan this QR code to link a device!']"
            )
            
            # Get canvas image
            qr_image_base64 = self.driver.execute_script(
                "return arguments[0].toDataURL('image/png').substring(21);",
                qr_canvas
            )
            
            # Decode and save
            qr_image_data = base64.b64decode(qr_image_base64)
            qr_path = SESSION_DIR / f"{self.session_name}_qr.png"
            
            with open(qr_path, 'wb') as f:
                f.write(qr_image_data)
            
            self.qr_code = qr_path
            logger.info(f"✓ QR code saved to {qr_path}")
            
        except Exception as e:
            logger.error(f"Failed to capture QR code: {e}")
    
    def send_message(self, phone_number, message_text):
        """
        Send a message to a phone number.
        
        Args:
            phone_number: Phone number with country code (e.g., "+1234567890")
            message_text: Message to send
        
        Returns:
            bool: True if message sent successfully
        """
        try:
            if not self.is_logged_in:
                logger.warning("Not logged in to WhatsApp")
                return False
            
            # Open chat with phone number
            wa_link = f"https://web.whatsapp.com/send?phone={phone_number}&text="
            self.driver.get(wa_link)
            
            # Wait for message box to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='3']"))
            )
            
            # Type message
            message_box = self.driver.find_element(
                By.XPATH,
                "//div[@contenteditable='true'][@data-tab='3']"
            )
            message_box.send_keys(message_text)
            
            # Send message
            send_button = self.driver.find_element(
                By.XPATH,
                "//button[@aria-label='Send']"
            )
            send_button.click()
            
            logger.info(f"✓ Message sent to {phone_number}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    def get_chats(self, limit=10):
        """
        Get list of recent chats.
        
        Args:
            limit: Number of chats to retrieve
        
        Returns:
            list: List of chat info dicts
        """
        try:
            if not self.is_logged_in:
                logger.warning("Not logged in to WhatsApp")
                return []
            
            chats = []
            chat_items = self.driver.find_elements(
                By.XPATH,
                "//div[@data-testid='chat-list-item']"
            )[:limit]
            
            for item in chat_items:
                try:
                    name = item.find_element(By.XPATH, ".//span[@title]").get_attribute("title")
                    chats.append({
                        "name": name,
                        "element": item
                    })
                except:
                    pass
            
            return chats
        
        except Exception as e:
            logger.error(f"Failed to get chats: {e}")
            return []
    
    def get_messages(self, chat_name, limit=20):
        """
        Get messages from a specific chat.
        
        Args:
            chat_name: Name of the chat
            limit: Number of messages to retrieve
        
        Returns:
            list: List of message dicts
        """
        try:
            if not self.is_logged_in:
                logger.warning("Not logged in to WhatsApp")
                return []
            
            # Find and click chat
            chats = self.get_chats(limit=50)
            for chat in chats:
                if chat["name"] == chat_name:
                    chat["element"].click()
                    time.sleep(1)
                    break
            
            # Get messages
            messages = []
            message_elements = self.driver.find_elements(
                By.XPATH,
                "//div[@data-testid='msg-container']"
            )[-limit:]
            
            for msg_elem in message_elements:
                try:
                    msg_text = msg_elem.text
                    msg_time = msg_elem.find_element(By.XPATH, ".//span[@data-testid='message_timestamp']").get_attribute("data-timestamp-ms")
                    is_incoming = "msg-in" in msg_elem.get_attribute("class")
                    
                    messages.append({
                        "text": msg_text,
                        "time": msg_time,
                        "incoming": is_incoming
                    })
                except:
                    pass
            
            return messages
        
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []
    
    def close(self):
        """Close WebDriver."""
        try:
            if self.driver:
                self.driver.quit()
                self.is_logged_in = False
                logger.info("✓ WebDriver closed")
        except Exception as e:
            logger.error(f"Error closing WebDriver: {e}")


class WhatsAppManager:
    """Manager for WhatsApp Web instances."""
    
    _instances = {}
    
    @classmethod
    def get_instance(cls, session_name="default"):
        """Get or create WhatsApp Web instance."""
        if session_name not in cls._instances:
            cls._instances[session_name] = WhatsAppWeb(session_name)
        return cls._instances[session_name]
    
    @classmethod
    def close_all(cls):
        """Close all instances."""
        for instance in cls._instances.values():
            instance.close()
        cls._instances.clear()
