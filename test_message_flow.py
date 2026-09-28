#!/usr/bin/env python3
"""
Diagnostic script to test WhatsApp message retrieval pipeline
"""
import sys
sys.path.insert(0, 'backend')

from app.whatsapp_service import WhatsAppManager
import logging
import time

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_message_pipeline():
    """Test the complete message retrieval and processing pipeline"""
    print("\n" + "="*70)
    print("Testing WhatsApp Message Retrieval Pipeline")
    print("="*70 + "\n")
    
    # Get WhatsApp instance
    wa = WhatsAppManager.get_instance('default')
    
    # Step 1: Check login status
    print("Step 1: Checking login status...")
    if not wa.is_logged_in:
        print("❌ NOT LOGGED IN - Please login first using /api/whatsapp/login")
        return
    print("✓ Logged in\n")
    
    # Step 2: Get chats
    print("Step 2: Fetching chats...")
    chats = wa.get_chats(limit=10)
    if not chats:
        print("❌ NO CHATS FOUND - This is the problem!")
        print("   Possible causes:")
        print("   - No chats loaded in WhatsApp Web")
        print("   - Chat selector not working with current DOM")
        print("   - Browser session lost")
        return
    print(f"✓ Found {len(chats)} chats:")
    for chat in chats[:3]:
        print(f"  - {chat.get('name', 'Unknown')}")
    print()
    
    # Step 3: Get messages from first chat
    if chats:
        first_chat = chats[0]
        chat_name = first_chat.get('name', '')
        print(f"Step 3: Fetching messages from '{chat_name}'...")
        
        messages = wa.get_messages(chat_name, limit=20)
        if not messages:
            print(f"❌ NO MESSAGES FOUND in '{chat_name}'")
            print("   Possible causes:")
            print("   - Chat has no messages")
            print("   - Message selector not working")
            print("   - Message extraction logic broken")
        else:
            print(f"✓ Found {len(messages)} messages:")
            for i, msg in enumerate(messages[-3:]):
                print(f"  {i+1}. Text: {msg.get('text', '')[:50]}")
                print(f"     Incoming: {msg.get('incoming', '?')}")
                print(f"     Timestamp: {msg.get('timestamp', 'N/A')}")
        print()
    
    # Step 4: Check listener status
    print("Step 4: Checking message listener status...")
    print(f"Listener active: {wa.listener_active}")
    print(f"Processed responses in queue: {len(wa.ai_processed_responses)}")
    if wa.ai_processed_responses:
        print("Recent responses:")
        for resp in wa.ai_processed_responses[:2]:
            print(f"  - From: {resp.get('from', '?')}")
            print(f"    Message: {resp.get('received_message', '')[:40]}...")
    print()
    
    # Step 5: Start listener if not running
    if not wa.listener_active:
        print("Step 5: Starting message listener...")
        result = wa.start_message_listener()
        print(f"Listener started: {result}")
        print("Waiting 10 seconds to collect messages...")
        time.sleep(10)
        print(f"Responses collected: {len(wa.ai_processed_responses)}")
    else:
        print("Step 5: Message listener already active")
    print()
    
    # Step 6: Summary
    print("="*70)
    print("DIAGNOSTIC SUMMARY")
    print("="*70)
    print(f"✓ Logged in: {wa.is_logged_in}")
    print(f"✓ Chats found: {len(wa.get_chats(limit=20))}")
    print(f"✓ Listener active: {wa.listener_active}")
    print(f"✓ Processed responses: {len(wa.ai_processed_responses)}")
    print()

if __name__ == '__main__':
    test_message_pipeline()
