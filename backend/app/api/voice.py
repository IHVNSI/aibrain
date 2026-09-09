"""Multilingual Voice Chat API - End-to-end voice processing pipeline."""
import logging
import os
from flask import Blueprint, request, jsonify
from ..auth import require_auth, current_user_context
from ..llm import build_llm, get_llm_settings
from ..multilingual_voice_pipeline import process_multilingual_voice

logger = logging.getLogger(__name__)
voice_bp = Blueprint("voice", __name__, url_prefix="/api/voice")

# Supported languages
SUPPORTED_LANGUAGES = ['igbo', 'yoruba', 'hausa', 'pidgin', 'english']


@voice_bp.route("/process", methods=["POST"])
@require_auth
def process_voice():
    """
    Complete multilingual voice processing pipeline.
    
    Accepts audio file → transcribes → translates → processes with LLM → 
    translates response → optional TTS output
    
    Request (multipart/form-data):
        - audio: Audio file (required) - WAV, MP3, OGG, FLAC
        - language: Language code (required) - igbo, yoruba, hausa, pidgin, english
        - instructions: What should AI do with the transcription (required)
        - return_audio: Whether to return audio response (optional, default: false)
        - voice_gender: Voice gender for TTS (optional) - MALE, FEMALE, NEUTRAL (default: NEUTRAL)
    
    Returns:
        {
            "success": true/false,
            "language": "igbo",
            "original_transcription": "Transcribed text in Igbo",
            "english_transcription": "English translation",
            "llm_response_english": "AI response in English",
            "llm_response_translated": "AI response in Igbo",
            "audio_response": "base64-encoded MP3 (if return_audio=true)",
            "steps": [...detailed step-by-step log...],
            "error": "error message if failed"
        }
    """
    try:
        # Check authentication
        ctx = current_user_context()
        if not ctx:
            return jsonify({"success": False, "error": "Authentication required"}), 401
        
        # Get form data
        if 'audio' not in request.files:
            return jsonify({"success": False, "error": "Missing 'audio' file"}), 400
        
        audio_file = request.files['audio']
        if not audio_file or audio_file.filename == '':
            return jsonify({"success": False, "error": "Invalid audio file"}), 400
        
        language = (request.form.get('language') or '').strip().lower()
        if not language:
            return jsonify({"success": False, "error": "Missing 'language' parameter"}), 400
        
        if language not in SUPPORTED_LANGUAGES:
            return jsonify({
                "success": False,
                "error": f"Unsupported language: {language}. Supported: {', '.join(SUPPORTED_LANGUAGES)}"
            }), 400
        
        instructions = (request.form.get('instructions') or '').strip()
        if not instructions:
            return jsonify({"success": False, "error": "Missing 'instructions' parameter"}), 400
        
        return_audio = request.form.get('return_audio', '').lower() in ('true', '1', 'yes')
        voice_gender = (request.form.get('voice_gender') or 'NEUTRAL').upper()
        
        # Save temporary audio file
        import tempfile
        import secure_filename
        
        # Use original filename but make it secure
        filename = audio_file.filename
        if filename:
            from werkzeug.utils import secure_filename as wz_secure_filename
            filename = wz_secure_filename(filename)
        else:
            filename = f"audio_{language}.wav"
        
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as tmp:
            audio_path = tmp.name
            audio_file.save(audio_path)
        
        try:
            # Build LLM instance
            llm = build_llm(get_llm_settings())
            
            # Process voice through pipeline
            logger.info(f"Processing voice in {language} for user {ctx.get('username')}")
            result = process_multilingual_voice(
                audio_path=audio_path,
                language=language,
                instructions=instructions,
                llm=llm,
                return_audio=return_audio,
                voice_gender=voice_gender
            )
            
            # Convert audio bytes to base64 if present
            if result.get('audio_response'):
                import base64
                result['audio_response'] = base64.b64encode(result['audio_response']).decode('utf-8')
            
            return jsonify(result), 200 if result.get('success') else 400
            
        finally:
            # Clean up temporary audio file
            if os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except Exception as e:
                    logger.warning(f"Could not delete temp audio file {audio_path}: {e}")
    
    except Exception as e:
        logger.error(f"Voice processing error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Voice processing failed: {str(e)}"
        }), 500


@voice_bp.route("/languages", methods=["GET"])
@require_auth
def get_supported_languages():
    """Get list of supported languages."""
    return jsonify({
        "success": True,
        "languages": SUPPORTED_LANGUAGES,
        "details": {
            "igbo": {"display": "Igbo", "native": "Igbo", "country": "Nigeria"},
            "yoruba": {"display": "Yoruba", "native": "Yoruba", "country": "Nigeria"},
            "hausa": {"display": "Hausa", "native": "Hausa", "country": "Nigeria"},
            "pidgin": {"display": "Nigerian Pidgin", "native": "Pidgin", "country": "Nigeria"},
            "english": {"display": "English", "native": "English", "country": "Multiple"},
        }
    }), 200


@voice_bp.route("/test-transcription", methods=["POST"])
@require_auth
def test_transcription():
    """
    Test audio transcription service availability.
    
    Request (JSON):
        {
            "language": "english|igbo|hausa|yoruba|pidgin",
            "stt_provider": "naijavox|web-speech|whisper|google-cloud-stt|azure-stt|elevenlabs" (optional)
        }
    
    Returns test result with service availability and configuration status.
    """
    try:
        ctx = current_user_context()
        if not ctx:
            return jsonify({"success": False, "error": "Authentication required"}), 401
        
        data = request.get_json(silent=True) or {}
        language = (data.get('language') or '').strip().lower()
        stt_provider = (data.get('stt_provider') or '').strip().lower()
        
        if not language or language not in SUPPORTED_LANGUAGES:
            return jsonify({"success": False, "error": f"Invalid language: {language}"}), 400
        
        # Default to NaijaVox if not specified
        if not stt_provider:
            stt_provider = 'naijavox'
        
        # Test specific STT providers
        test_results = {
            'naijavox': _test_naijavox_stt(language),
            'web-speech': _test_web_speech_stt(language),
            'whisper': _test_whisper_stt(language),
            'google-cloud-stt': _test_google_cloud_stt(language),
            'azure-stt': _test_azure_stt(language),
            'elevenlabs': _test_elevenlabs_stt(language),
        }
        
        requested_result = test_results.get(stt_provider, {})
        if requested_result.get('success'):
            return jsonify(requested_result), 200
        else:
            return jsonify(requested_result), 503
            
    except Exception as e:
        logger.error(f"STT test error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Test error: {str(e)}"
        }), 500


def _test_naijavox_stt(language):
    """Test NaijaVox-2.0 STT availability."""
    try:
        from ..multilingual_voice_pipeline import transcribe_audio
        logger.info(f"✓ NaijaVox STT is available for {language}")
        return {
            "success": True,
            "provider": "NaijaVox-2.0",
            "language": language,
            "message": f"✓ NaijaVox-2.0 STT is available for {language}",
            "cost": "Free (local)",
            "quality": "Good"
        }
    except Exception as e:
        return {
            "success": False,
            "provider": "NaijaVox-2.0",
            "error": f"NaijaVox not available: {str(e)}",
            "setup": "pip install librosa torchaudio transformers torch"
        }


def _test_web_speech_stt(language):
    """Test Web Speech API availability (client-side)."""
    return {
        "success": True,
        "provider": "Web Speech API",
        "language": language,
        "message": "✓ Web Speech API is available (browser-based)",
        "cost": "Free (local)",
        "quality": "Good",
        "note": "Uses browser's built-in speech recognition"
    }


def _test_whisper_stt(language):
    """Test OpenAI Whisper availability."""
    try:
        openai_key = os.getenv('OPENAI_API_KEY', '').strip()
        if not openai_key:
            return {
                "success": False,
                "provider": "OpenAI Whisper",
                "error": "OPENAI_API_KEY not configured",
                "setup": "Set OPENAI_API_KEY in .env"
            }
        
        logger.info(f"✓ Whisper STT is configured for {language}")
        return {
            "success": True,
            "provider": "OpenAI Whisper",
            "language": language,
            "message": f"✓ OpenAI Whisper is configured for {language}",
            "cost": "$0.02 per 1 minute of audio",
            "quality": "Excellent"
        }
    except Exception as e:
        return {
            "success": False,
            "provider": "OpenAI Whisper",
            "error": str(e)
        }


def _test_google_cloud_stt(language):
    """Test Google Cloud Speech-to-Text availability."""
    try:
        credentials_path = os.getenv('GOOGLE_CLOUD_STT_CREDENTIALS_PATH', '').strip()
        if not credentials_path or not os.path.exists(credentials_path):
            return {
                "success": False,
                "provider": "Google Cloud STT",
                "error": "GOOGLE_CLOUD_STT_CREDENTIALS_PATH not configured",
                "setup": "Set GOOGLE_CLOUD_STT_CREDENTIALS_PATH in .env"
            }
        
        logger.info(f"✓ Google Cloud STT is available for {language}")
        return {
            "success": True,
            "provider": "Google Cloud Speech-to-Text",
            "language": language,
            "message": f"✓ Google Cloud STT is available for {language}",
            "cost": "$0.006 per 15 seconds",
            "quality": "Excellent"
        }
    except Exception as e:
        return {
            "success": False,
            "provider": "Google Cloud STT",
            "error": str(e)
        }


def _test_azure_stt(language):
    """Test Azure Speech-to-Text availability."""
    try:
        azure_key = os.getenv('AZURE_SPEECH_KEY', '').strip()
        azure_region = os.getenv('AZURE_SPEECH_REGION', '').strip()
        
        if not azure_key or not azure_region:
            return {
                "success": False,
                "provider": "Azure Speech-to-Text",
                "error": "AZURE_SPEECH_KEY or AZURE_SPEECH_REGION not configured",
                "setup": "Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION in .env"
            }
        
        logger.info(f"✓ Azure STT is configured for {language}")
        return {
            "success": True,
            "provider": "Azure Speech-to-Text",
            "language": language,
            "message": f"✓ Azure STT is configured for {language}",
            "cost": "Free tier: 5000 minutes/month; Pay-as-you-go: $1 per hour",
            "quality": "Excellent"
        }
    except Exception as e:
        return {
            "success": False,
            "provider": "Azure Speech-to-Text",
            "error": str(e)
        }


def _test_elevenlabs_stt(language):
    """Test ElevenLabs Scribe API availability."""
    try:
        elevenlabs_key = os.getenv('ELEVENLABS_API_KEY', '').strip()
        if not elevenlabs_key:
            return {
                "success": False,
                "provider": "ElevenLabs Scribe",
                "error": "ELEVENLABS_API_KEY not configured",
                "setup": "Set ELEVENLABS_API_KEY in .env"
            }
        
        logger.info(f"✓ ElevenLabs STT is configured for {language}")
        return {
            "success": True,
            "provider": "ElevenLabs Scribe API",
            "language": language,
            "message": f"✓ ElevenLabs Scribe is configured for {language}",
            "cost": "Premium service with diarization",
            "quality": "Premium"
        }
    except Exception as e:
        return {
            "success": False,
            "provider": "ElevenLabs Scribe",
            "error": str(e)
        }


@voice_bp.route("/test-translation", methods=["POST"])
@require_auth
def test_translation():
    """
    Test text translation between languages.
    
    Request (JSON):
        {
            "text": "Text to translate",
            "source_language": "igbo",
            "target_language": "english"
        }
    
    Returns:
        {
            "success": true/false,
            "source_language": "igbo",
            "target_language": "english",
            "original_text": "Original text",
            "translated_text": "Translated text"
        }
    """
    try:
        ctx = current_user_context()
        if not ctx:
            return jsonify({"success": False, "error": "Authentication required"}), 401
        
        data = request.get_json(silent=True) or {}
        text = (data.get('text') or '').strip()
        source = (data.get('source_language') or '').strip().lower()
        target = (data.get('target_language') or '').strip().lower()
        
        if not text or not source or not target:
            return jsonify({"success": False, "error": "Missing required fields"}), 400
        
        from ..translation import translate
        
        translated = translate(text, source, target)
        
        return jsonify({
            "success": True,
            "source_language": source,
            "target_language": target,
            "original_text": text,
            "translated_text": translated
        }), 200
    
    except Exception as e:
        logger.error(f"Translation test error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@voice_bp.route("/test-tts", methods=["POST"])
@require_auth
def test_tts():
    """
    Test text-to-speech synthesis.
    
    Request (JSON):
        {
            "text": "Text to speak",
            "language": "igbo",
            "voice_gender": "NEUTRAL"  # optional
        }
    
    Returns:
        {
            "success": true/false,
            "language": "igbo",
            "audio_response": "base64-encoded MP3",
            "message": "Audio synthesis message"
        }
    """
    try:
        ctx = current_user_context()
        if not ctx:
            return jsonify({"success": False, "error": "Authentication required"}), 401
        
        data = request.get_json(silent=True) or {}
        text = (data.get('text') or '').strip()
        language = (data.get('language') or '').strip().lower()
        voice_gender = (data.get('voice_gender') or 'NEUTRAL').upper()
        
        if not text or not language:
            return jsonify({"success": False, "error": "Missing 'text' or 'language'"}), 400
        
        from ..multilingual_voice_pipeline import synthesize_speech
        import base64
        
        audio_bytes = synthesize_speech(text, language, voice_gender)
        
        if audio_bytes:
            return jsonify({
                "success": True,
                "language": language,
                "audio_response": base64.b64encode(audio_bytes).decode('utf-8'),
                "message": f"Audio synthesis successful for {language}"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Audio synthesis failed. Ensure Google Cloud TTS is configured."
            }), 400
    
    except Exception as e:
        logger.error(f"TTS test error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
