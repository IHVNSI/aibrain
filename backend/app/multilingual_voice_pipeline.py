"""
Multilingual Voice Pipeline for Nigerian Languages
Handles: STT → Transcribe → Translate → LLM → Translate → TTS
Supports: Igbo, Yoruba, Hausa, Nigerian Pidgin, English
"""
import logging
import os
import json
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

# Language mappings for various services
LANGUAGE_CONFIGS = {
    'igbo': {
        'google_stt': 'ig-NG',
        'google_tts': 'ig-NG',
        'naijavox': 'igbo',
        'whisper': 'ig',
        'translate': 'ig',
        'display': 'IGBO',
    },
    'yoruba': {
        'google_stt': 'yo-NG',
        'google_tts': 'yo-NG',
        'naijavox': 'yoruba',
        'whisper': 'yo',
        'translate': 'yo',
        'display': 'YORUBA',
    },
    'hausa': {
        'google_stt': 'ha-NG',
        'google_tts': 'ha-NG',
        'naijavox': 'hausa',
        'whisper': 'ha',
        'translate': 'ha',
        'display': 'HAUSA',
    },
    'pidgin': {
        'google_stt': 'en-US',  # Google doesn't have specific Pidgin STT
        'google_tts': 'en-US',  # Will use English with special handling
        'naijavox': 'pidgin',
        'whisper': 'en',
        'translate': 'pcm',
        'display': 'PIDGIN',
    },
    'english': {
        'google_stt': 'en-US',
        'google_tts': 'en-US',
        'naijavox': 'nigerian_english',
        'whisper': 'en',
        'translate': 'en',
        'display': 'ENGLISH',
    },
}


def get_language_config(language: str) -> Dict:
    """Get service-specific language configuration."""
    lang_lower = language.lower()
    return LANGUAGE_CONFIGS.get(lang_lower, LANGUAGE_CONFIGS['english'])


def transcribe_audio(audio_path: str, language: str, llm=None) -> Optional[str]:
    """
    Transcribe audio using NaijaVox-2.0 (primary) or Whisper (fallback).
    
    Args:
        audio_path: Path to audio file
        language: Target language (igbo, yoruba, hausa, pidgin, english)
        llm: Optional LLM instance for fallback
    
    Returns:
        Transcribed text in the source language, or None
    """
    try:
        from .api.multiperson_chat import perform_speech_to_text
        
        logger.info(f"Transcribing audio in {language}...")
        transcript = perform_speech_to_text(audio_path, language, llm, stt_model='auto')
        
        if transcript:
            logger.info(f"✓ Transcription ({language}): {len(transcript)} chars")
            return transcript.strip()
        
        logger.warning(f"Transcription returned empty for {language}")
        return None
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return None


def translate_to_english(text: str, source_language: str) -> str:
    """
    Translate transcribed text to English for LLM processing.
    
    Args:
        text: Transcribed text in source language
        source_language: Language of the transcription (igbo, yoruba, hausa, pidgin)
    
    Returns:
        English translation
    """
    try:
        from .translation import translate
        
        if source_language.lower() == 'english':
            return text
        
        logger.info(f"Translating to English from {source_language}...")
        english_text = translate(text, source_language, 'english')
        logger.info(f"✓ Translation to English: {len(english_text)} chars")
        
        return english_text
        
    except Exception as e:
        logger.error(f"Translation to English error: {e}")
        return text


def process_with_llm(english_text: str, instructions: str, llm) -> str:
    """
    Process English text with LLM using provided instructions.
    
    Args:
        english_text: English transcription
        instructions: What the user wants the AI to do
        llm: LLM instance
    
    Returns:
        LLM response in English
    """
    try:
        if not llm:
            logger.warning("LLM not configured")
            return english_text
        
        logger.info(f"Processing with LLM: {len(english_text)} input chars")
        
        prompt = f"""{instructions}

Input: {english_text}

Please provide a response based on the instructions above."""
        
        # Try to use chat method if available
        if hasattr(llm, 'chat'):
            response = llm.chat([
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": prompt}
            ])
        elif hasattr(llm, 'generate_sql_response'):
            response = llm.generate_sql_response(prompt, context="")
        else:
            logger.warning("LLM has no supported method for response generation")
            return english_text
        
        if response:
            logger.info(f"✓ LLM Response: {len(response)} chars")
            return response.strip()
        
        return english_text
        
    except Exception as e:
        logger.error(f"LLM processing error: {e}")
        return english_text


def translate_from_english(english_response: str, target_language: str) -> str:
    """
    Translate LLM response back to target language.
    
    Args:
        english_response: LLM response in English
        target_language: Target language (igbo, yoruba, hausa, pidgin)
    
    Returns:
        Translation of response in target language
    """
    try:
        from .translation import translate
        
        if target_language.lower() == 'english':
            return english_response
        
        logger.info(f"Translating response to {target_language}...")
        translated = translate(english_response, 'english', target_language)
        logger.info(f"✓ Translation to {target_language}: {len(translated)} chars")
        
        return translated
        
    except Exception as e:
        logger.error(f"Translation from English error: {e}")
        return english_response


def synthesize_speech(text: str, language: str, gender: str = 'NEUTRAL') -> Optional[bytes]:
    """
    Convert text to speech using Google Cloud TTS.
    
    Args:
        text: Text to synthesize
        language: Target language (igbo, yoruba, hausa, pidgin, english)
        gender: Voice gender (MALE, FEMALE, NEUTRAL)
    
    Returns:
        Audio bytes (MP3 format), or None if synthesis fails
    """
    try:
        from google.cloud import texttospeech
        
        # Check if credentials are configured
        credentials_path = os.getenv('GOOGLE_CLOUD_TTS_CREDENTIALS_PATH') or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not credentials_path:
            logger.warning("Google Cloud TTS credentials not configured")
            return None
        
        # Set credentials if path provided
        if credentials_path and not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        config = get_language_config(language)
        lang_code = config['google_tts']
        
        logger.info(f"Synthesizing speech in {language} ({lang_code})...")
        
        client = texttospeech.TextToSpeechClient()
        
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        voice = texttospeech.VoiceSelectionParams(
            language_code=lang_code,
            ssml_gender=getattr(texttospeech.SsmlVoiceGender, gender, texttospeech.SsmlVoiceGender.NEUTRAL)
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        if response.audio_content:
            logger.info(f"✓ Speech synthesis: {language} ({len(response.audio_content)} bytes)")
            return response.audio_content
        
        return None
        
    except ImportError:
        logger.warning("google-cloud-texttospeech not installed")
        return None
    except Exception as e:
        logger.error(f"Speech synthesis error: {e}")
        return None


def process_multilingual_voice(
    audio_path: str,
    language: str,
    instructions: str,
    llm,
    return_audio: bool = False,
    voice_gender: str = 'NEUTRAL'
) -> Dict:
    """
    Complete multilingual voice pipeline:
    Audio → STT → Transcribe → Translate → LLM → Translate → TTS
    
    Args:
        audio_path: Path to input audio file
        language: Voice language (igbo, yoruba, hausa, pidgin, english)
        instructions: What the AI should do with the transcription
        llm: LLM instance for processing
        return_audio: Whether to generate audio response (True) or text only (False)
        voice_gender: Voice gender for TTS (MALE, FEMALE, NEUTRAL)
    
    Returns:
        Dict with:
        - original_transcription: Transcribed text in original language
        - english_transcription: Translated to English
        - llm_response_english: LLM response in English
        - llm_response_translated: LLM response translated back to original language
        - audio_response: MP3 bytes (if return_audio=True), else None
        - success: Whether entire pipeline succeeded
        - language: Language of all non-English fields
        - steps: Detailed log of each step
    """
    steps = []
    
    try:
        # Step 1: Transcribe audio
        logger.info(f"🎤 Step 1: Transcribing audio in {language}...")
        transcription = transcribe_audio(audio_path, language, llm)
        
        if not transcription:
            logger.error("Transcription failed")
            return {
                "success": False,
                "error": "Failed to transcribe audio",
                "language": language,
                "steps": steps
            }
        
        steps.append({
            "step": 1,
            "name": "Audio Transcription",
            "status": "✓",
            "result": transcription,
            "language": language
        })
        
        # Step 2: Translate to English
        logger.info(f"🌍 Step 2: Translating to English...")
        english_text = translate_to_english(transcription, language)
        
        steps.append({
            "step": 2,
            "name": "Translate to English",
            "status": "✓",
            "result": english_text,
            "language": "english"
        })
        
        # Step 3: Process with LLM
        logger.info(f"🤖 Step 3: Processing with LLM...")
        llm_response_english = process_with_llm(english_text, instructions, llm)
        
        steps.append({
            "step": 3,
            "name": "LLM Processing",
            "status": "✓",
            "result": llm_response_english,
            "language": "english"
        })
        
        # Step 4: Translate response back to target language
        logger.info(f"🌍 Step 4: Translating response to {language}...")
        llm_response_translated = translate_from_english(llm_response_english, language)
        
        steps.append({
            "step": 4,
            "name": "Translate Response",
            "status": "✓",
            "result": llm_response_translated,
            "language": language
        })
        
        # Step 5: Optional - Synthesize audio response
        audio_response = None
        if return_audio:
            logger.info(f"🔊 Step 5: Synthesizing speech response in {language}...")
            audio_response = synthesize_speech(llm_response_translated, language, voice_gender)
            
            if audio_response:
                steps.append({
                    "step": 5,
                    "name": "Text-to-Speech",
                    "status": "✓",
                    "audio_bytes": len(audio_response),
                    "language": language
                })
            else:
                steps.append({
                    "step": 5,
                    "name": "Text-to-Speech",
                    "status": "⚠",
                    "message": "TTS not configured or failed, returning text only",
                    "language": language
                })
        
        logger.info(f"✅ Multilingual voice pipeline completed successfully")
        
        return {
            "success": True,
            "language": language,
            "original_transcription": transcription,
            "english_transcription": english_text,
            "llm_response_english": llm_response_english,
            "llm_response_translated": llm_response_translated,
            "audio_response": audio_response,
            "return_audio": return_audio,
            "steps": steps
        }
        
    except Exception as e:
        logger.error(f"Multilingual pipeline error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "language": language,
            "steps": steps
        }
