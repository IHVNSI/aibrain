"""WhatsApp Web automation service - Login via QR code and send/receive messages."""
import logging
import os
import time
import base64
import re
import threading
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
        self.listener_active = False
        self.listener_paused = False  # Pause listener during send operations
        self.last_processed_messages = {}  # Track processed messages to avoid duplicates
        self.ai_processed_responses = []  # Store AI responses to incoming messages
        self.driver_lock = threading.RLock()  # Reentrant lock for thread-safe driver access (allows same thread to re-acquire)
    
    def setup_driver(self, retry_count=0, max_retries=5):
        """Setup Chrome WebDriver with minimal, proven-stable options.
        
        Retries if Chrome is already running with the same user-data-dir.
        Runs with minimal UI (user can see Chrome window if needed for debugging).
        """
        try:
            chrome_options = Options()
            
            # Ensure session directory exists
            self.session_path.mkdir(exist_ok=True, parents=True)
            chrome_options.add_argument(f"user-data-dir={self.session_path}")
            
            # MINIMAL, PROVEN-STABLE FLAGS ONLY
            # Removed: --headless, --single-process, and excessive --disable-* flags
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            service = Service(ChromeDriverManager().install())
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            logger.info("✓ Chrome WebDriver initialized successfully")
            return True
        
        except Exception as e:
            error_msg = str(e).lower()
            
            # If Chrome crashed or session not created, wait and retry
            if any(x in error_msg for x in ["session not created", "chrome failed to start", "chrome instance exited", "crashed", "devtoolsactiveport"]):
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff: 1s, 2s, 4s, 8s, 16s
                    logger.warning(f"Chrome startup issue (attempt {retry_count + 1}/{max_retries}), retrying in {wait_time}s...")
                    
                    # Close any existing Chrome processes
                    import subprocess
                    try:
                        subprocess.run(['taskkill', '/IM', 'chrome.exe', '/F'], 
                                     stderr=subprocess.DEVNULL, 
                                     stdout=subprocess.DEVNULL)
                        logger.info("Cleaned up existing Chrome processes")
                    except:
                        pass
                    
                    time.sleep(wait_time)
                    return self.setup_driver(retry_count=retry_count + 1, max_retries=max_retries)
                else:
                    logger.error(f"Failed to setup WebDriver after {max_retries} retries: {e}")
                    return False
            
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
    
    def start_login_async(self):
        """
        Start login process in the background and return QR code immediately.
        If already logged in on the browser, automatically connect.
        Always prints QR code to terminal.
        
        Returns:
            dict: {"success": bool, "qr_code": base64_string or None, "message": str}
        """
        try:
            import threading
            
            # Check if already logged in (in memory)
            if self.is_logged_in:
                logger.info("✓ Already logged in (in memory)")
                return {
                    "success": True,
                    "message": "Already logged in",
                    "logged_in": True,
                    "qr_code": None
                }
            
            # Use lock to prevent race condition with message listener
            with self.driver_lock:
                # If driver doesn't exist, setup
                if not self.driver:
                    logger.info("Setting up Chrome WebDriver...")
                    if not self.setup_driver():
                        logger.error("Failed to setup WebDriver")
                        return {"success": False, "message": "Failed to setup WebDriver"}
                    
                    logger.info("Opening WhatsApp Web (this may take 10-30 seconds)...")
                    try:
                        self.driver.get("https://web.whatsapp.com/")
                        # WhatsApp Web takes significant time to load fully
                        logger.info("Waiting for WhatsApp Web to load (10 seconds minimum)...")
                        time.sleep(10)
                        logger.info("✓ WhatsApp Web initial load complete")
                    except Exception as e:
                        logger.error(f"Failed to open WhatsApp Web: {e}")
                        return {"success": False, "message": f"Failed to open WhatsApp: {str(e)}"}
                
                # Check if already logged in on the browser
                logger.info("Checking if already logged in on browser...")
                if self._check_login_successful():
                    logger.info("✓ Already logged in to WhatsApp Web!")
                    self.is_logged_in = True
                    
                    # Print to terminal
                    print("\n" + "="*60)
                    print("✓ WhatsApp is already logged in!")
                    print("✓ App is now connected to WhatsApp Web")
                    print("="*60 + "\n")
                    logger.info("✓ Printed status to terminal")
                    
                    # Start message listener in background
                    thread = threading.Thread(target=self.start_message_listener, daemon=True)
                    thread.start()
                    
                    return {
                        "success": True,
                        "message": "Already logged in - Connected!",
                        "logged_in": True,
                        "qr_code": None
                    }
                
                # Not logged in, wait for QR code
                logger.info("Not logged in yet - waiting for QR code...")
                qr_found = False
                try:
                    # Wait up to 30 seconds for QR code canvas to appear
                    logger.info("Waiting for QR code element (up to 30 seconds)...")
                    qr_element = WebDriverWait(self.driver, 30).until(
                        EC.presence_of_element_located((By.XPATH, "//canvas[@aria-label='Scan this QR code to link a device!']"))
                    )
                    logger.info("✓ QR code element found on page")
                    qr_found = True
                except Exception as e:
                    logger.warning(f"QR code canvas not found within 30 seconds: {e}")
                    # Try alternative check
                    try:
                        logger.info("Trying alternative QR code detection...")
                        qr_element = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//canvas"))
                        )
                        logger.info("✓ Found canvas element (may be QR code)")
                        qr_found = True
                    except Exception as e2:
                        logger.debug(f"Alternative QR code check also failed: {e2}")
                
                if not qr_found:
                    # QR code not found, might already be logged in or page not fully loaded
                    logger.warning("QR code not found, checking page and login status...")
                    
                    # Debug: Get current page title and URL
                    try:
                        current_url = self.driver.current_url
                        page_title = self.driver.title
                        logger.info(f"Current page URL: {current_url}")
                        logger.info(f"Page title: {page_title}")
                    except Exception as debug_e:
                        logger.debug(f"Could not get page info: {debug_e}")
                    
                    # Wait a bit more for page to fully load
                    logger.info("Waiting additional 5 seconds for page to fully load...")
                    time.sleep(5)
                    
                    # Check if now logged in
                    if self._check_login_successful():
                        logger.info("✓ Now logged in to WhatsApp Web!")
                        self.is_logged_in = True
                        
                        # Print to terminal
                        print("\n" + "="*60)
                        print("✓ WhatsApp is now logged in!")
                        print("✓ App is now connected to WhatsApp Web")
                        print("="*60 + "\n")
                        
                        # Start message listener in background
                        thread = threading.Thread(target=self.start_message_listener, daemon=True)
                        thread.start()
                        
                        return {
                            "success": True,
                            "message": "Now logged in - Connected!",
                            "logged_in": True,
                            "qr_code": None
                        }
                    
                    # Try one more time to find QR code
                    logger.info("Trying to find QR code one more time...")
                    try:
                        qr_element = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, "//canvas"))
                        )
                        logger.info("✓ Found canvas element on retry")
                        qr_found = True
                    except Exception as retry_e:
                        logger.error(f"QR code retry failed: {retry_e}")
                        logger.error("Could not find QR code or login. WhatsApp Web may not have loaded properly.")
                        return {
                            "success": False,
                            "message": "WhatsApp Web failed to load properly. Please refresh and try again."
                        }
                
                # If we get here, QR code was found, proceed with capture
                
                # Capture QR code
                try:
                    self._capture_qr_code()
                    qr_base64 = self.get_qr_code_base64()
                    
                    if not qr_base64:
                        logger.error("QR code capture returned empty base64")
                        return {"success": False, "message": "Failed to capture QR code - empty data"}
                    
                    logger.info(f"✓ QR code captured (size: {len(qr_base64)} bytes)")
                    
                    # Print QR code to terminal
                    self.print_qr_to_terminal()
                    
                except Exception as e:
                    logger.error(f"Failed to capture QR code: {e}", exc_info=True)
                    return {"success": False, "message": f"Failed to capture QR code: {str(e)}"}
            
            # Start background thread to wait for scan completion (outside lock)
            thread = threading.Thread(target=self._wait_for_scan_background, daemon=True)
            thread.start()
            
            return {
                "success": True,
                "message": "QR code ready - Please scan with your phone",
                "qr_code": f"data:image/png;base64,{qr_base64}",
                "logged_in": False,
                "polling_url": "/api/whatsapp/status"
            }
        
        except Exception as e:
            logger.error(f"Failed during login process: {e}", exc_info=True)
            return {"success": False, "message": f"Login error: {str(e)}"}
    
    def _check_login_successful(self):
        """Check if WhatsApp login was successful using multiple selectors."""
        try:
            # Try multiple indicators of successful login
            login_indicators = [
                "//div[@data-testid='pane-side']",  # Chat sidebar
                "//div[@data-testid='chat-list']",   # Chat list
                "//div[@aria-label='Search the web']",  # Search bar (appears when logged in)
                "//div[contains(@class, 'two')]",    # Two-pane layout class
                "//div[@role='main']",               # Main content area
                "//span[@aria-label='Profile']",     # Profile indicator
            ]
            
            # Try each indicator
            for indicator in login_indicators:
                try:
                    WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((By.XPATH, indicator))
                    )
                    logger.info(f"✓ Found login indicator: {indicator}")
                    return True
                except:
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Error checking login: {e}")
            return False
    
    def _wait_for_scan_background(self):
        """Background thread to wait for QR code scan completion."""
        try:
            logger.info("Background: Waiting for QR code scan...")
            max_wait = 120  # 2 minutes
            start_time = time.time()
            check_interval = 2  # Check every 2 seconds
            
            while time.time() - start_time < max_wait:
                try:
                    # Check if login was successful using multiple selectors
                    if self._check_login_successful():
                        logger.info("✓ WhatsApp QR code scanned successfully!")
                        self.is_logged_in = True
                        time.sleep(2)  # Wait for full load
                        
                        # Start message listener after successful login
                        self.start_message_listener()
                        return
                except Exception as e:
                    logger.debug(f"Login check attempt failed: {e}")
                
                time.sleep(check_interval)
            
            logger.warning("Background: QR code scan timeout")
        except Exception as e:
            logger.error(f"Background scan error: {e}")
    
    def _capture_qr_code(self):
        """Capture and save QR code image."""
        try:
            qr_canvas = self.driver.find_element(
                By.XPATH, 
                "//canvas[@aria-label='Scan this QR code to link a device!']"
            )
            
            # Get canvas image - try direct method
            qr_image_base64 = None
            full_data_url = self.driver.execute_script(
                "return arguments[0].toDataURL('image/png');",
                qr_canvas
            )
            
            if full_data_url and full_data_url.startswith("data:image/png;base64,"):
                qr_image_base64 = full_data_url.replace("data:image/png;base64,", "")
                logger.debug("✓ QR code captured from canvas")
            else:
                logger.error(f"Invalid data URL format: {full_data_url[:50] if full_data_url else 'None'}")
                return
            
            # Decode and save
            qr_image_data = base64.b64decode(qr_image_base64)
            qr_path = SESSION_DIR / f"{self.session_name}_qr.png"
            
            with open(qr_path, 'wb') as f:
                f.write(qr_image_data)
            
            self.qr_code = qr_path
            self.qr_code_base64 = qr_image_base64  # Store base64 for API responses
            logger.info(f"✓ QR code saved to {qr_path} ({len(qr_image_base64)} bytes)")
            
        except Exception as e:
            logger.error(f"Failed to capture QR code: {e}", exc_info=True)
    
    def get_qr_code_base64(self):
        """Get QR code as base64 string for embedding in API response."""
        if hasattr(self, 'qr_code_base64'):
            return self.qr_code_base64
        elif self.qr_code and self.qr_code.exists():
            try:
                with open(self.qr_code, 'rb') as f:
                    qr_data = f.read()
                    return base64.b64encode(qr_data).decode('utf-8')
            except Exception as e:
                logger.error(f"Failed to read QR code: {e}")
        return None
    
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
            
            # Temporarily pause listener to avoid driver contention
            self.listener_paused = True
            time.sleep(0.5)  # Wait for listener to finish current operation
            
            try:
                # Try to acquire lock with timeout (prevent infinite wait)
                acquired = self.driver_lock.acquire(timeout=10)
                if not acquired:
                    logger.error("Failed to acquire driver lock (timeout)")
                    return False
                
                try:
                    # Check if driver is still responsive
                    if not self.driver:
                        logger.error("Driver is None")
                        return False
                    
                    logger.info(f"Opening WhatsApp chat with {phone_number}...")
                    
                    # Open chat with phone number
                    wa_link = f"https://web.whatsapp.com/send?phone={phone_number}&text="
                    self.driver.get(wa_link)
                    
                    # Wait for message box to load (try multiple selectors)
                    message_box = None
                    message_box_found = False
                    
                    # Selector 1: Standard contenteditable div
                    try:
                        logger.debug("Trying selector 1: contenteditable div")
                        message_box = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@role='textbox']"))
                        )
                        logger.debug("✓ Found message box with selector 1")
                        message_box_found = True
                    except:
                        pass
                    
                    # Selector 2: Data-tab selector
                    if not message_box_found:
                        try:
                            logger.debug("Trying selector 2: data-tab div")
                            message_box = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='3']"))
                            )
                            logger.debug("✓ Found message box with selector 2")
                            message_box_found = True
                        except:
                            pass
                    
                    # Selector 3: Simple contenteditable
                    if not message_box_found:
                        try:
                            logger.debug("Trying selector 3: simple contenteditable")
                            message_box = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
                            )
                            logger.debug("✓ Found message box with selector 3")
                            message_box_found = True
                        except:
                            pass
                    
                    if not message_box_found:
                        logger.error("Could not find message box after trying 3 selectors")
                        return False
                    
                    # Clear any existing text
                    message_box.clear()
                    
                    # Type message
                    logger.info("Typing message...")
                    message_box.send_keys(message_text)
                    
                    # Wait a bit for message to be typed
                    time.sleep(0.5)
                    
                    # Find and click send button (try multiple selectors)
                    send_button_found = False
                    
                    # Selector 1: aria-label="Send"
                    try:
                        logger.debug("Trying selector 1: Send button with aria-label")
                        send_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Send']"))
                        )
                        logger.debug("✓ Found send button with selector 1")
                        send_button.click()
                        send_button_found = True
                    except:
                        pass
                    
                    # Selector 2: Icon in footer
                    if not send_button_found:
                        try:
                            logger.debug("Trying selector 2: Send button with span")
                            send_button = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='send']"))
                            )
                            logger.debug("✓ Found send button with selector 2")
                            send_button.click()
                            send_button_found = True
                        except:
                            pass
                    
                    # Selector 3: Just press Enter instead
                    if not send_button_found:
                        try:
                            logger.debug("Trying selector 3: Send via Enter key")
                            message_box.send_keys(Keys.RETURN)
                            logger.debug("✓ Message sent via Enter key")
                            send_button_found = True
                        except:
                            pass
                    
                    if not send_button_found:
                        logger.error("Could not find send button after trying 3 methods")
                        return False
                    
                    logger.info(f"✓ Message sent to {phone_number}")
                    return True
                
                finally:
                    self.driver_lock.release()
            
            finally:
                # Resume listener
                self.listener_paused = False
        
        except Exception as e:
            logger.error(f"Failed to send message: {e}", exc_info=True)
            self.listener_paused = False
            self.listener_paused = False
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
            
            # Skip if paused
            if self.listener_paused:
                return []
            
            # Try to acquire lock with timeout (non-blocking for listener operations)
            acquired = self.driver_lock.acquire(timeout=5)
            if not acquired:
                logger.debug("Could not acquire lock for get_chats (may be busy with send_message)")
                return []
            
            try:
                return self._get_chats_unlocked(limit)
            finally:
                self.driver_lock.release()
        
        except Exception as e:
            logger.error(f"Failed to get chats: {e}")
            return []

    def _get_chats_unlocked(self, limit=10):
        """Internal version of get_chats without locking (assumes lock is already held)."""
        chats = []
        
        # Try primary selector
        try:
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
        except Exception as e:
            logger.debug(f"Primary chat selector failed: {e}")
        
        # If no chats found, try alternative selectors
        if not chats:
            try:
                logger.debug("Trying alternative chat list selectors...")
                # Try div with role="option"
                chat_items = self.driver.find_elements(By.XPATH, "//div[@role='option']")[:limit]
                for item in chat_items:
                    try:
                        name = item.text.strip()
                        if name:
                            chats.append({"name": name, "element": item})
                    except:
                        pass
            except Exception as e:
                logger.debug(f"Alternative selector failed: {e}")
        
        return chats
    
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
            
            # Skip if paused
            if self.listener_paused:
                return []
            
            # Try to acquire lock with timeout (non-blocking for listener operations)
            acquired = self.driver_lock.acquire(timeout=5)
            if not acquired:
                logger.debug("Could not acquire lock for get_messages (may be busy with send_message)")
                return []
            
            try:
                # Find and click chat
                chats = self._get_chats_unlocked(limit=50)
                for chat in chats:
                    if chat["name"] == chat_name:
                        try:
                            chat["element"].click()
                            time.sleep(1)
                        except:
                            pass
                        break
                
                # Get messages (try multiple selectors)
                messages = []
                message_elements = []
                
                # Selector 1: Standard msg-container
                try:
                    logger.debug("Trying selector 1: msg-container")
                    message_elements = self.driver.find_elements(
                        By.XPATH,
                        "//div[@data-testid='msg-container']"
                    )
                    if message_elements:
                        logger.debug(f"✓ Found {len(message_elements)} messages with selector 1")
                except Exception as e:
                    logger.debug(f"Selector 1 failed: {e}")
                
                # Selector 2: Message role-based
                if not message_elements:
                    try:
                        logger.debug("Trying selector 2: message role")
                        message_elements = self.driver.find_elements(
                            By.XPATH,
                            "//div[@role='button' and contains(@class, 'message')]"
                        )
                        if message_elements:
                            logger.debug(f"✓ Found {len(message_elements)} messages with selector 2")
                    except Exception as e:
                        logger.debug(f"Selector 2 failed: {e}")
                
                # Selector 3: Generic div with text content
                if not message_elements:
                    try:
                        logger.debug("Trying selector 3: generic message div")
                        message_elements = self.driver.find_elements(
                            By.XPATH,
                            "//div[contains(@class, 'msg') or contains(@class, 'message')]"
                        )
                        if message_elements:
                            logger.debug(f"✓ Found {len(message_elements)} messages with selector 3")
                    except Exception as e:
                        logger.debug(f"Selector 3 failed: {e}")
                
                if not message_elements:
                    logger.warning("Could not find any messages with any selector")
                    return []
                
                # Process messages (get last 'limit' messages)
                for msg_elem in message_elements[-limit:]:
                    try:
                        msg_text = msg_elem.text
                        if not msg_text:
                            continue
                        
                        # Try to get timestamp
                        msg_time = None
                        try:
                            timestamp_elem = msg_elem.find_element(
                                By.XPATH, 
                                ".//span[@data-testid='message_timestamp']"
                            )
                            msg_time = timestamp_elem.get_attribute("data-timestamp-ms")
                        except:
                            try:
                                # Fallback: try aria-label with time
                                msg_time = msg_elem.get_attribute("aria-label")
                            except:
                                pass
                        
                        # Determine if incoming or outgoing with improved detection
                        is_incoming = False
                        try:
                            class_attr = msg_elem.get_attribute("class") or ""
                            data_attr = msg_elem.get_attribute("data-testid") or ""
                            
                            # Check multiple indicators for incoming messages
                            # Method 1: Check class attribute
                            if "msg-in" in class_attr or "incoming" in class_attr.lower():
                                is_incoming = True
                            # Method 2: Check for message on the left (typically incoming)
                            elif "msg-left" in class_attr or "message-in" in class_attr:
                                is_incoming = True
                            # Method 3: Check for outgoing indicators (if found, it's NOT incoming)
                            elif "msg-out" in class_attr or "outgoing" in class_attr.lower() or "message-out" in class_attr:
                                is_incoming = False
                            # Method 4: Check data attributes
                            elif "msg-in" in data_attr:
                                is_incoming = True
                            # Method 5: Check parent element for sender info
                            else:
                                try:
                                    parent = msg_elem.find_element(By.XPATH, "./ancestor::div[@data-testid='message-pane-header']/..")
                                    # If no exception, assume it could be incoming
                                    is_incoming = True
                                except:
                                    # Default to True for now - process all messages and let AI routing handle access control
                                    # This ensures we don't miss legitimate messages
                                    is_incoming = True
                        except Exception as e:
                            logger.debug(f"Error determining message direction: {e}")
                            # Default to True to not miss messages
                            is_incoming = True
                        
                        messages.append({
                            "text": msg_text,
                            "time": msg_time,
                            "timestamp": msg_time,  # Add both "time" and "timestamp" for compatibility
                            "incoming": is_incoming
                        })
                        logger.debug(f"Extracted message: {msg_text[:50]}... (incoming={is_incoming})")
                    
                    except Exception as e:
                        logger.debug(f"Error processing message element: {e}")
                        continue
                
                logger.info(f"✓ Retrieved {len(messages)} messages from {chat_name}")
                return messages
            
            finally:
                self.driver_lock.release()
        
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []
    
    def start_message_listener(self):
        """Start listening for incoming WhatsApp messages in background thread."""
        try:
            if self.listener_active:
                logger.info("Message listener already active")
                return True
            
            import threading
            self.listener_active = True
            thread = threading.Thread(target=self._listen_for_messages_background, daemon=True)
            thread.start()
            logger.info("✓ Message listener started in background thread")
            return True
        
        except Exception as e:
            logger.error(f"Failed to start message listener: {e}", exc_info=True)
            return False
    
    def _cleanup_processed_messages(self):
        """
        Cleanup mechanism: keep only the last 1000 processed messages to prevent memory bloat.
        Uses a simple FIFO approach - removes oldest entries when limit exceeded.
        """
        max_cached_messages = 1000
        current_count = len(self.last_processed_messages)
        
        if current_count > max_cached_messages:
            # Convert dict to list of items, sort by nothing (just get order), and keep last 1000
            # Since we can't sort by insertion order easily, we'll just clear and start fresh
            # when we exceed the limit to prevent unbounded memory growth
            old_count = current_count
            
            # Keep a conservative approach: clear old entries but keep most recent
            # We'll create a new dict with only the most recent entries
            items = list(self.last_processed_messages.items())
            self.last_processed_messages = dict(items[-max_cached_messages:])
            
            logger.debug(f"Cleaned up processed messages cache: {old_count} → {len(self.last_processed_messages)}")
    
    def _get_message_hash(self, chat_name, message_text, timestamp=None):
        """
        Create a unique hash for a message to better identify duplicates.
        Uses combination of chat_name, message_text content hash, and optional timestamp.
        
        Args:
            chat_name: Name of the chat
            message_text: The message text
            timestamp: Optional message timestamp for uniqueness
        
        Returns:
            str: Hash identifier for the message
        """
        import hashlib
        # Use content hash to better handle duplicate messages with exact same text
        content = f"{chat_name}:{message_text}"
        content_hash = hashlib.md5(content.encode()).hexdigest()[:16]
        
        if timestamp:
            return f"{content_hash}_{timestamp}"
        return content_hash
    
    def _listen_for_messages_background(self):
        """Background thread that listens for new incoming messages and processes them as AI prompts."""
        try:
            logger.info("🎧 Message listener thread started")
            
            while self.listener_active and self.is_logged_in:
                try:
                    # Skip operations if paused (e.g., during send_message)
                    if self.listener_paused:
                        time.sleep(1)
                        continue
                    
                    # Get list of chats
                    chats = self.get_chats(limit=20)
                    
                    if not chats:
                        time.sleep(5)
                        continue
                    
                    # Check each chat for new messages
                    for chat in chats:
                        # Skip if paused
                        if self.listener_paused:
                            break
                        
                        try:
                            chat_name = chat.get("name", "")
                            if not chat_name:
                                continue
                            
                            # Get messages from this chat
                            messages = self.get_messages(chat_name, limit=50)
                            
                            # Process new/unprocessed messages in reverse order (oldest first)
                            for msg in reversed(messages):
                                # Extract message details
                                message_text = msg.get('text', '')
                                message_timestamp = msg.get('timestamp', '')
                                
                                # Skip empty messages
                                if not message_text or not message_text.strip():
                                    continue
                                
                                # Generate better message hash for deduplication
                                msg_hash = self._get_message_hash(chat_name, message_text, message_timestamp)
                                
                                # Skip if already processed
                                if msg_hash in self.last_processed_messages:
                                    logger.debug(f"Skipping duplicate message from {chat_name}: {message_text[:30]}...")
                                    continue
                                
                                # Only process incoming messages
                                if not msg.get("incoming", False):
                                    self.last_processed_messages[msg_hash] = True
                                    continue
                                
                                # Mark as processed
                                self.last_processed_messages[msg_hash] = True
                                
                                # Process this message as AI prompt
                                logger.info(f"📨 New WhatsApp message from {chat_name}: {message_text[:60]}...")
                                
                                ai_response = self.handle_message_with_ai(
                                    message_text=message_text,
                                    sender_name=chat_name
                                )
                                
                                if ai_response.get("success", False):
                                    # Store processed response
                                    response_obj = {
                                        "from": chat_name,
                                        "received_message": message_text,
                                        "ai_response": ai_response.get("response", ""),
                                        "timestamp": datetime.now().isoformat(),
                                        "ready_to_send": ai_response.get("ready_to_send", False)
                                    }
                                    self.ai_processed_responses.insert(0, response_obj)
                                    
                                    # Keep only last 50 responses in memory
                                    if len(self.ai_processed_responses) > 50:
                                        self.ai_processed_responses = self.ai_processed_responses[:50]
                                    
                                    logger.info(f"✓ AI response generated and queued: {ai_response.get('response', '')[:50]}...")
                                else:
                                    logger.warning(f"⚠️ Failed to generate AI response for {chat_name}: {ai_response.get('error', 'Unknown error')}")
                        
                        except Exception as e:
                            logger.error(f"Error processing chat {chat.get('name', 'Unknown')}: {e}", exc_info=True)
                            continue
                    
                    # Periodic cleanup of processed messages cache (every 10 polls ~ 50 seconds)
                    self._cleanup_processed_messages()
                    
                    # Poll every 5 seconds
                    time.sleep(5)
                
                except Exception as e:
                    logger.error(f"Error in message listener loop: {e}", exc_info=True)
                    time.sleep(5)
        
        except Exception as e:
            logger.error(f"Message listener background thread error: {e}", exc_info=True)
            self.listener_active = False
    
    def get_ai_processed_responses(self):
        """Get AI responses generated from listened messages."""
        return self.ai_processed_responses
    
    def clear_processed_responses(self):
        """Clear the processed responses queue."""
        count = len(self.ai_processed_responses)
        self.ai_processed_responses = []
        logger.info(f"Cleared {count} processed responses")
        return count
    
    def print_qr_to_terminal(self):
        """Display QR code instructions in terminal (actual image shown in Modal)."""
        try:
            # Check if QR code exists
            if not hasattr(self, 'qr_code_base64') or not self.qr_code_base64:
                logger.warning("No QR code available")
                return False
            
            qr_file_path = self.session_path / f"{self.session_name}_qr.png"
            
            # Print helpful instructions to terminal
            print("\n" + "="*70)
            print("📱 WHATSAPP WEB LOGIN")
            print("="*70)
            print("\n✅ QR Code is ready for scanning!\n")
            print("OPTIONS TO SCAN:")
            print("-"*70)
            print("1️⃣  RECOMMENDED: Use the Modal in the web app")
            print("    → QR code displays clearly in the login modal")
            print("    → Scan with your WhatsApp phone camera")
            print("")
            print("2️⃣  ALTERNATIVE: Open QR code file directly")
            print(f"    → File: {qr_file_path}")
            print("    → Open this file with an image viewer")
            print("    → Scan with your WhatsApp phone camera")
            print("")
            print("3️⃣  MANUAL: Type WhatsApp login URL in browser")
            print("    → https://web.whatsapp.com/")
            print("-"*70)
            print("\n⏳ Waiting for scan... (Timeout: 2 minutes)\n")
            print("="*70 + "\n")
            
            logger.info("✓ QR code instructions printed to terminal")
            return True
        
        except Exception as e:
            logger.error(f"Error printing QR code instructions: {e}")
            return False
    
    def get_incoming_messages(self, chat_name=None):
        """
        Get incoming/new messages.
        
        Args:
            chat_name: Specific chat to check (None for all chats)
        
        Returns:
            list: List of incoming message dicts with sender info
        """
        try:
            if not self.is_logged_in:
                logger.warning("Not logged in to WhatsApp")
                return []
            
            messages = []
            
            # Get all messages and filter for incoming
            if chat_name:
                all_messages = self.get_messages(chat_name)
            else:
                # Get from first few chats
                chats = self.get_chats(limit=5)
                for chat in chats:
                    chat_messages = self.get_messages(chat["name"])
                    for msg in chat_messages:
                        if msg.get("incoming"):
                            msg["from"] = chat["name"]
                            messages.append(msg)
            
            return messages
        
        except Exception as e:
            logger.error(f"Error getting incoming messages: {e}")
            return []
    
    def _detect_sender_type(self, sender_name):
        """
        Detect if sender is a staff member or verified client.
        
        Args:
            sender_name: Name/identifier of sender
        
        Returns:
            dict: {"type": "staff" | "client" | "external", "id": int or None, "context": dict}
        """
        try:
            from .models import User, AuthorizedContact
            from . import db
            
            if not sender_name:
                return {"type": "external", "id": None, "context": {}}
            
            # Check if sender is a staff member (in User table)
            try:
                user = User.query.filter(
                    (User.username.ilike(sender_name)) | 
                    (User.email.ilike(sender_name)) |
                    ((User.first_name + ' ' + User.last_name).ilike(f"%{sender_name}%"))
                ).first()
                
                if user:
                    logger.info(f"✓ Sender identified as staff: {user.username} (ID: {user.id})")
                    return {
                        "type": "staff",
                        "id": user.id,
                        "context": {
                            "username": user.username,
                            "name": f"{user.first_name} {user.last_name}".strip(),
                            "email": user.email,
                            "company_id": user.company_id,
                            "branch_id": user.branch_id
                        }
                    }
            except Exception as e:
                logger.debug(f"Error checking staff status: {e}")
            
            # Check if sender is a verified client (in AuthorizedContact)
            try:
                contact = AuthorizedContact.query.filter(
                    (AuthorizedContact.contact.ilike(sender_name)) |
                    (AuthorizedContact.contact.ilike(f"%{sender_name}%"))
                ).first()
                
                if contact and contact.is_active:
                    logger.info(f"✓ Sender identified as verified client: {contact.contact} (ID: {contact.id}, Level: {contact.permission_level})")
                    return {
                        "type": "client",
                        "id": contact.id,
                        "context": {
                            "contact": contact.contact,
                            "contact_type": contact.contact_type,
                            "permission_level": contact.permission_level,
                            "description": contact.description
                        }
                    }
            except Exception as e:
                logger.debug(f"Error checking client status: {e}")
            
            # Not staff or verified client
            logger.info(f"⚠️ Sender is external (not staff, not verified client): {sender_name}")
            return {"type": "external", "id": None, "context": {}}
        
        except Exception as e:
            logger.error(f"Error detecting sender type: {e}")
            return {"type": "external", "id": None, "context": {}}
    
    def _build_sender_context_prompt(self, sender_info):
        """
        Build system prompt context based on sender type.
        
        Args:
            sender_info: dict from _detect_sender_type()
        
        Returns:
            str: System prompt instructions
        """
        sender_type = sender_info.get("type", "external")
        sender_context = sender_info.get("context", {})
        
        if sender_type == "staff":
            # Staff member - can provide comprehensive information
            return f"""You are an AI assistant for the business WhatsApp channel.
You are speaking with an internal staff member: {sender_context.get('name', 'Staff Member')}

You have access to comprehensive business information including:
- All customer data (jobs, parts orders, vehicles, service records)
- Staff records and internal information
- Financial data and analytics
- Inventory and supply chain information
- All business operations data

Respond professionally and provide detailed information as needed.
However, respect any access control settings configured for this staff member's role.
For highly sensitive data, warn if access may be restricted.
"""
        
        elif sender_type == "client":
            # Verified client - provide ONLY their specific data
            contact = sender_context.get("contact", "Client")
            permission = sender_context.get("permission_level", "SELECT_ONLY")
            
            return f"""You are an AI assistant for the business WhatsApp channel.
You are speaking with a verified client: {contact}

IMPORTANT - Data Access Policy for Verified Clients:
1. You can ONLY provide information specific to this client's account, including:
   - Their jobs and service orders
   - Their parts orders and inventory
   - Their vehicles and maintenance history
   - Their service diagnoses and reports
   - Their invoices and payment history

2. DO NOT provide:
   - Information about other clients or contacts
   - Staff information or organizational structure
   - Financial data beyond this client's transactions
   - Pricing information not specific to their agreements
   - Business strategy or internal operations

3. When asked for client-specific data, look it up from business records.
   When asked for general business questions, you can answer from public knowledge.
   When data is restricted, politely decline and suggest contacting their account manager.

Permission Level: {permission} - Provide read-only access unless explicitly approved.
Be helpful, professional, and concise in responses.
"""
        
        else:  # external
            # External/unknown contact - only general business information
            return """You are an AI assistant for the business WhatsApp channel.
You are speaking with an external contact.

Data Access Policy for External Contacts:
1. You can provide general business information:
   - Business hours and contact information
   - General product/service information
   - Public pricing and offerings
   - FAQ and common questions

2. DO NOT provide:
   - Specific customer data or records
   - Staff information
   - Internal operations or strategy
   - Confidential business information
   - Personal data of any kind

3. For client-specific inquiries, ask them to:
   - Provide their account reference number
   - Or request them to speak with their account manager

Be helpful within these limits, professional, and concise.
"""
    
    def route_message_to_ai(self, message_text, sender_name=None):
        """
        Route message to AI and get response with sender-based filtering.
        
        Args:
            message_text: The message text to process
            sender_name: Name/identifier of sender (for access control)
        
        Returns:
            dict: {"success": bool, "response": str, "sender_type": str, "error": str}
        """
        try:
            from .llm.factory import build_llm
            
            llm = build_llm()
            if not llm:
                return {"success": False, "error": "LLM not configured"}
            
            # Detect sender type and get context-specific prompt
            sender_info = self._detect_sender_type(sender_name)
            system_prompt = self._build_sender_context_prompt(sender_info)
            
            # Build the full prompt
            user_prompt = f"""Message from {sender_name or 'User'}:

{message_text}

Please provide a helpful, concise response (keep it brief for WhatsApp).
Be professional but friendly."""
            
            # Get AI response
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response = llm.chat(messages)
            
            if response:
                logger.info(f"✓ AI generated response for {sender_info.get('type')} ({sender_name}): {response[:50]}...")
                return {
                    "success": True,
                    "response": response,
                    "sender_type": sender_info.get("type"),
                    "access_controlled": sender_info.get("type") in ["staff", "client"]
                }
            else:
                return {"success": False, "error": "Failed to generate response", "sender_type": sender_info.get("type")}
        
        except Exception as e:
            logger.error(f"Error routing message to AI: {e}")
            return {"success": False, "error": str(e)}
    
    def _strip_markdown(self, text):
        """
        Strip all markdown formatting from text for WhatsApp compatibility.
        
        Args:
            text: Text with potential markdown formatting
        
        Returns:
            str: Text with markdown formatting removed
        """
        # Bold: **text** or __text__
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        
        # Italic: *text* or _text_
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'_(.+?)_', r'\1', text)
        
        # Strikethrough: ~text~
        text = re.sub(r'~(.+?)~', r'\1', text)
        
        # Links: [text](url)
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
        
        # Code blocks: ```code```
        text = re.sub(r'`{3}[\s\S]*?`{3}', '', text)
        
        # Inline code: `code`
        text = re.sub(r'`(.+?)`', r'\1', text)
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def handle_message_with_ai(self, message_text, sender_name=None):
        """
        Handle incoming message: route to AI and prepare for sending.
        
        Args:
            message_text: The message to handle
            sender_name: Sender's name
        
        Returns:
            dict: {"success": bool, "response": str, "ready_to_send": bool}
        """
        try:
            # Input validation
            if not message_text or not isinstance(message_text, str):
                return {
                    "success": False,
                    "error": "Message text is empty or invalid",
                    "ready_to_send": False
                }
            
            # Check reasonable length (WhatsApp limit is ~4096 chars, limit input to 2000)
            if len(message_text) > 2000:
                return {
                    "success": False,
                    "error": "Message text exceeds maximum length (2000 characters)",
                    "ready_to_send": False
                }
            
            # Route to AI
            ai_result = self.route_message_to_ai(message_text, sender_name)
            
            if not ai_result.get("success", False):
                error_msg = ai_result.get("error", "Unknown error")
                logger.warning(f"AI routing failed for message from {sender_name}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "ready_to_send": False
                }
            
            response_text = ai_result.get("response", "")
            
            if not response_text or not isinstance(response_text, str):
                logger.error(f"AI returned invalid response for {sender_name}")
                return {
                    "success": False,
                    "error": "AI generated invalid response",
                    "ready_to_send": False
                }
            
            # Strip markdown formatting for WhatsApp compatibility
            response_text = self._strip_markdown(response_text)
            
            if not response_text:  # Ensure we still have content after stripping
                logger.error(f"Response became empty after markdown stripping")
                return {
                    "success": False,
                    "error": "Response is empty after formatting",
                    "ready_to_send": False
                }
            
            logger.info(f"✓ Successfully processed AI response for {sender_name}: {response_text[:50]}...")
            return {
                "success": True,
                "response": response_text,
                "ready_to_send": True,
                "from_sender": sender_name
            }
        
        except Exception as e:
            logger.error(f"Error handling message with AI: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Processing error: {str(e)}",
                "ready_to_send": False
            }
    
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
