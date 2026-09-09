"""Translation utilities for multi-language support."""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Language code mappings (IETF BCP 47 format for Google Translate)
LANGUAGE_CODES = {
    'english': 'en',
    'igbo': 'ig',
    'hausa': 'ha',
    'yoruba': 'yo',
    'pidgin': 'pcm',  # Nigerian Pidgin
}

# Language names for prompts
LANGUAGE_NAMES = {
    'igbo': 'Igbo',
    'hausa': 'Hausa',
    'yoruba': 'Yoruba',
    'pidgin': 'Nigerian Pidgin',
    'english': 'English',
}


def translate_with_google_cloud(text: str, source_lang: str, target_lang: str) -> Optional[str]:
    """
    Translate using Google Cloud Translation API.
    
    Args:
        text: Text to translate
        source_lang: Source language code (e.g., 'en', 'ig', 'yo')
        target_lang: Target language code (e.g., 'en', 'ig', 'yo')
    
    Returns:
        Translated text or None if translation fails
    """
    try:
        from google.cloud import translate_v2
        
        # Get credentials from environment
        credentials_path = os.getenv('GOOGLE_CLOUD_TRANSLATION_CREDENTIALS_PATH')
        if credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        client = translate_v2.Client()
        result = client.translate_text(text, source_language=source_lang, target_language=target_lang)
        
        translated = result.get('translatedText', '')
        if translated:
            logger.info(f"✓ Google Cloud Translation: {source_lang} → {target_lang} ({len(text)} → {len(translated)} chars)")
            return translated
        
        return None
        
    except ImportError:
        logger.debug("google-cloud-translate not installed")
        return None
    except Exception as e:
        logger.warning(f"Google Cloud Translation error: {e}")
        return None


def translate_with_llm(text: str, source_language: str, target_language: str) -> Optional[str]:
    """
    Translate using the configured LLM as fallback.
    
    Args:
        text: Text to translate
        source_language: Source language name (e.g., 'english', 'igbo', 'yoruba')
        target_language: Target language name (e.g., 'english', 'igbo', 'yoruba')
    
    Returns:
        Translated text or None if translation fails
    """
    try:
        from .llm import build_llm
        
        llm = build_llm()
        if not llm:
            logger.warning(f"LLM not configured for translation")
            return None
        
        source_name = LANGUAGE_NAMES.get(source_language.lower(), source_language)
        target_name = LANGUAGE_NAMES.get(target_language.lower(), target_language)
        
        # Create translation prompt
        if source_language.lower() == target_language.lower():
            return text
        
        prompt = f"""Translate the following {source_name} text to {target_name}.
Return ONLY the translation, nothing else. Do not add explanations or notes.

{source_name} text: {text}

{target_name} translation:"""
        
        response = llm.generate_sql_response(prompt, context="") if hasattr(llm, 'generate_sql_response') else llm.chat([
            {"role": "system", "content": f"You are a professional translator. Translate from {source_name} to {target_name}."},
            {"role": "user", "content": prompt}
        ])
        
        if response:
            translation = response.strip()
            logger.info(f"✓ LLM Translation: {source_language} → {target_language}")
            return translation
        
        return None
        
    except Exception as e:
        logger.error(f"LLM translation error: {e}")
        return None


def translate(text: str, source_language: str, target_language: str) -> str:
    """
    Translate text from source to target language.
    Priority: Google Cloud → LLM → Original text
    
    Args:
        text: Text to translate
        source_language: Source language (english, igbo, hausa, yoruba, pidgin)
        target_language: Target language (english, igbo, hausa, yoruba, pidgin)
    
    Returns:
        Translated text, or original if translation fails
    """
    if not text or not text.strip():
        return text
    
    # Normalize language names
    source = source_language.lower()
    target = target_language.lower()
    
    # If same language, return as-is
    if source == target:
        return text
    
    # Get language codes
    source_code = LANGUAGE_CODES.get(source, source)
    target_code = LANGUAGE_CODES.get(target, target)
    
    logger.info(f"Translating from {source} ({source_code}) to {target} ({target_code})")
    
    # Try Google Cloud first
    result = translate_with_google_cloud(text, source_code, target_code)
    if result:
        return result
    
    # Fall back to LLM
    result = translate_with_llm(text, source, target)
    if result:
        return result
    
    # Final fallback: return original text
    logger.warning(f"Translation failed for {source}→{target}, returning original text")
    return text


def translate_to_english(text: str, source_language: str) -> str:
    """
    Translate text to English using the configured LLM provider.
    
    Args:
        text: Text to translate
        source_language: Source language code (english, igbo, hausa, yoruba)
    
    Returns:
        Translated text in English, or original text if already English
    """
    return translate(text, source_language, 'english')


def detect_language_and_translate(text: str, source_language: Optional[str] = None) -> tuple:
    """
    Detect or use provided language and translate to English if needed.
    
    Args:
        text: Text to potentially translate
        source_language: Optional language code (if not provided, assumes the user's setting)
    
    Returns:
        Tuple of (translated_text, original_language_code)
    """
    if not text or not text.strip():
        return text, 'en'
    
    # Use provided language or default to English
    lang = source_language or 'english'
    translated = translate_to_english(text, lang)
    
    return translated, LANGUAGE_CODES.get(lang.lower(), 'en')


def prepare_multilingual_input(user_input: str, user_language: str) -> dict:
    """
    Prepare user input for processing by translating if needed.
    
    Args:
        user_input: Raw user input
        user_language: Language code from user settings
    
    Returns:
        Dict with original_text, translated_text, and detected_language
    """
    translated_text, lang_code = detect_language_and_translate(user_input, user_language)
    
    return {
        'original_text': user_input,
        'translated_text': translated_text,
        'original_language': user_language,
        'language_code': lang_code,
        'is_translated': user_language.lower() != 'english',
    }
