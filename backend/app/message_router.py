"""LLM-based message routing - Determines if user wants to send email, WhatsApp, or something else.

This module uses ONLY the LLM to decide the intent, replacing all heuristic detection.
The LLM analyzes the user request and decides:
- send_email: Send an email message
- send_whatsapp: Send a WhatsApp message
- respond_whatsapp: Reply to a WhatsApp message
- database_query: Query for information
- other: Something else (greeting, help, etc.)
"""
import logging
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MessageRouter:
    """Routes user messages to appropriate handlers based on LLM analysis."""
    
    @staticmethod
    def route_message(llm, user_query: str, conversation_history: Optional[list] = None) -> Dict[str, Any]:
        """
        Use LLM to decide the intent of the user message.
        
        Args:
            llm: LLM provider instance
            user_query: The user's input message
            conversation_history: Previous messages for context
            
        Returns:
            Dict with:
            {
                "intent": "send_email|send_whatsapp|respond_whatsapp|database_query|other",
                "recipient": "email/phone if applicable",
                "subject": "if email",
                "message_body": "the message to send",
                "context": "extracted context/data requirements",
                "confidence": 0.0-1.0,
                "reasoning": "why this intent was chosen"
            }
        """
        if llm is None:
            return {
                "intent": "database_query",
                "confidence": 0.0,
                "reasoning": "No LLM available for routing",
                "error": "LLM not configured"
            }
        
        try:
            # Build conversation context (last 8 messages)
            transcript = ""
            if conversation_history:
                transcript = "\n".join([
                    f"{m.get('type', '').upper()}: {m.get('content', '')}"
                    for m in conversation_history[-8:]
                ])
            
            # Routing prompt - ONLY the LLM decides
            routing_prompt = """You are a message routing assistant. Analyze the user's request and determine EXACTLY what they want to do.

INTENT TYPES:
1. send_email: User wants to send an email message (e.g., "send email to john", "email the invoice to Bob", "send a message to support")
2. send_whatsapp: User wants to send a WhatsApp message (e.g., "send WhatsApp to 1234567890", "message him on WhatsApp", "WhatsApp the update")
3. respond_whatsapp: User wants to reply to a WhatsApp message they received (e.g., "reply to the message", "respond on WhatsApp", "reply to John's WhatsApp")
4. database_query: User wants information/data (e.g., "show invoices", "get customer list", "what's the revenue?")
5. other: Greeting, help request, general question (e.g., "hello", "help me", "how do I...?")

CRITICAL RULES:
- NEVER guess. Use ONLY the information in the user's message.
- If the user explicitly mentions "email", "WhatsApp", "message", "call", etc., use that as the primary signal.
- For ambiguous requests, ask yourself: "Did the user explicitly ask to SEND something to someone?"
- If yes → send_email or send_whatsapp (depending on explicit mention)
- If no → likely database_query or other

RESPONSE FORMAT (ONLY JSON, no extra text):
{
    "intent": "send_email|send_whatsapp|respond_whatsapp|database_query|other",
    "recipient": "extracted recipient (email, phone number, or name) or null",
    "subject": "if email: subject line or null",
    "message_body": "the message content to send or null",
    "data_query": "if database_query: what data is needed or null",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation of why this intent"
}

Examples:
- "Send invoice for job 1 to john@example.com" → {"intent": "send_email", "recipient": "john@example.com", "subject": "Invoice for Job 1", "message_body": "See attached invoice for job 1", ...}
- "Message him on WhatsApp that the order is ready" → {"intent": "send_whatsapp", "recipient": "him", "message_body": "The order is ready", ...}
- "Show me invoices for Q4" → {"intent": "database_query", "data_query": "invoices for Q4", ...}
- "Hi there" → {"intent": "other", "message_body": "Hi there", ...}
"""
            
            # Prepare messages for LLM
            messages = [
                {"role": "system", "content": routing_prompt}
            ]
            
            if transcript:
                messages.append({
                    "role": "user",
                    "content": f"Conversation history:\n{transcript}\n\n--- NEW REQUEST ---\n{user_query}"
                })
            else:
                messages.append({
                    "role": "user",
                    "content": f"User request:\n{user_query}"
                })
            
            # Call LLM
            logger.info(f"🧠 Routing message via LLM: {user_query[:80]}")
            raw_response = llm.chat(messages)
            
            # Parse JSON response
            result = MessageRouter._parse_llm_response(raw_response)
            
            logger.info(f"📍 Intent detected: {result.get('intent')} (confidence: {result.get('confidence', 0)})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Message routing error: {e}", exc_info=True)
            return {
                "intent": "database_query",
                "confidence": 0.0,
                "reasoning": f"Routing error: {str(e)}",
                "error": str(e)
            }
    
    @staticmethod
    def _parse_llm_response(raw_response: str) -> Dict[str, Any]:
        """Extract and parse JSON from LLM response."""
        if not raw_response:
            return {
                "intent": "other",
                "confidence": 0.0,
                "reasoning": "Empty LLM response"
            }
        
        # Try to find JSON in response
        try:
            # Clean up response
            cleaned = raw_response.strip()
            
            # Remove markdown code blocks
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
                cleaned = cleaned.rstrip("```").strip()
            
            # Parse JSON
            parsed = json.loads(cleaned)
            
            # Validate required fields
            if "intent" not in parsed:
                parsed["intent"] = "other"
            
            if "confidence" not in parsed:
                parsed["confidence"] = 0.7  # Default confidence
            
            if "reasoning" not in parsed:
                parsed["reasoning"] = "LLM routing completed"
            
            # Ensure confidence is 0-1
            try:
                confidence = float(parsed.get("confidence", 0.7))
                parsed["confidence"] = max(0.0, min(1.0, confidence))
            except (ValueError, TypeError):
                parsed["confidence"] = 0.7
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM JSON response: {e}")
            logger.debug(f"Raw response: {raw_response[:200]}")
            
            # Return a safe default
            return {
                "intent": "other",
                "confidence": 0.3,
                "reasoning": f"Could not parse LLM response: {str(e)}",
                "raw_response": raw_response[:500]
            }


def analyze_message_intent(llm, user_message: str, history: list = None) -> Dict[str, Any]:
    """
    Convenience function - wrapper around MessageRouter.route_message().
    
    Args:
        llm: LLM provider
        user_message: The user's message
        history: Conversation history
        
    Returns:
        Routing result with intent and extracted parameters
    """
    return MessageRouter.route_message(llm, user_message, history)
