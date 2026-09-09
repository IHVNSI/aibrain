"""Multi-person chat analysis API - capture conversations and generate AI suggestions."""
import logging
import json
import os
from flask import Blueprint, request, jsonify
from ..auth import require_auth, current_user_context
from ..llm import build_llm, get_llm_settings
from ..translation import prepare_multilingual_input, detect_language_and_translate

logger = logging.getLogger(__name__)
multiperson_bp = Blueprint("multiperson", __name__, url_prefix="/api/multiperson")


@multiperson_bp.route("/multiperson-analyze", methods=["POST"])
@require_auth
def analyze_multiperson_conversation():
    """
    Analyze a multi-person conversation and generate AI suggestion.
    
    Body: {
        "conversations": [{ participant, originalText, translatedText, timestamp }],
        "instructions": "what AI should do",
        "participants": ["Person1", "Person2", ...]
    }
    """
    ctx = current_user_context()
    if not (ctx.get('is_admin') or ctx.get('is_central_admin')):
        return jsonify({"success": False, "error": "Only admins can use this feature"}), 403
    
    data = request.get_json(silent=True) or {}
    conversations = data.get("conversations", [])
    instructions = data.get("instructions", "").strip()
    
    if not conversations or not instructions:
        return jsonify({"success": False, "error": "Missing conversations or instructions"}), 400
    
    try:
        # Build conversation context
        conv_text = "MULTI-PERSON CONVERSATION:\n"
        for idx, conv in enumerate(conversations, 1):
            participant = conv.get("participant", "Unknown")
            text = conv.get("translatedText") or conv.get("originalText", "")
            conv_text += f"\n{idx}. {participant}: {text}"
        
        # Get user's language setting for context
        user_language = data.get("voiceInputLanguage", "english")
        
        # Build the prompt for AI
        llm = build_llm(get_llm_settings())
        if not llm:
            return jsonify({"success": False, "error": "LLM not configured"}), 503
        
        prompt = f"""You are an AI assistant analyzing a multi-person conversation.

{conv_text}

INSTRUCTIONS: {instructions}

Please analyze this conversation and provide a clear, actionable suggestion for what you recommend should be done next. 
Your suggestion should be specific, practical, and based on the conversation content.
Format your response clearly with:
1. Summary of the conversation
2. Key points identified
3. Recommended action(s)
4. Reasoning for this recommendation"""
        
        # Get AI suggestion
        suggestion = llm.chat([
            {"role": "system", "content": "You are a helpful AI assistant analyzing multi-person conversations."},
            {"role": "user", "content": prompt}
        ])
        
        if not suggestion:
            return jsonify({"success": False, "error": "Failed to generate suggestion"}), 500
        
        logger.info(f"Generated multiperson analysis suggestion")
        
        return jsonify({
            "success": True,
            "suggestion": suggestion.strip()
        }), 200
        
    except Exception as e:
        logger.error(f"Multiperson analysis error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@multiperson_bp.route("/multiperson-execute", methods=["POST"])
@require_auth
def execute_multiperson_action():
    """
    Execute the AI-suggested action with user approval.
    
    Body: {
        "suggestion": "AI's recommended action",
        "conversations": [...],
        "approval": true
    }
    """
    ctx = current_user_context()
    if not (ctx.get('is_admin') or ctx.get('is_central_admin')):
        return jsonify({"success": False, "error": "Only admins can use this feature"}), 403
    
    data = request.get_json(silent=True) or {}
    suggestion = data.get("suggestion", "").strip()
    approval = data.get("approval", False)
    
    if not suggestion or not approval:
        return jsonify({"success": False, "error": "Missing suggestion or approval not given"}), 400
    
    try:
        llm = build_llm(get_llm_settings())
        if not llm:
            return jsonify({"success": False, "error": "LLM not configured"}), 503
        
        # Generate execution plan
        exec_prompt = f"""The user has approved the following AI suggestion and wants to execute it:

SUGGESTION: {suggestion}

Based on this approved suggestion, provide a detailed execution summary that includes:
1. Step-by-step implementation plan
2. Expected outcomes
3. Timeline/priority
4. Any required follow-ups

Format this as an actionable report."""
        
        result = llm.chat([
            {"role": "system", "content": "You are an AI assistant helping execute approved actions."},
            {"role": "user", "content": exec_prompt}
        ])
        
        if not result:
            return jsonify({"success": False, "error": "Failed to generate execution plan"}), 500
        
        logger.info(f"Executed multiperson action with approval")
        
        return jsonify({
            "success": True,
            "result": result.strip(),
            "status": "executed",
            "approval_timestamp": json.dumps({"approved_at": str(__import__('datetime').datetime.utcnow())})
        }), 200
        
    except Exception as e:
        logger.error(f"Multiperson execution error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@multiperson_bp.route("/multiperson-refine", methods=["POST"])
@require_auth
def refine_multiperson_suggestion():
    """
    Refine the AI suggestion based on user feedback.
    
    Body: {
        "currentSuggestion": "current suggestion",
        "feedback": "user feedback",
        "conversations": [...],
        "instructions": "original instructions"
    }
    """
    ctx = current_user_context()
    if not (ctx.get('is_admin') or ctx.get('is_central_admin')):
        return jsonify({"success": False, "error": "Only admins can use this feature"}), 403
    
    data = request.get_json(silent=True) or {}
    current_suggestion = data.get("currentSuggestion", "").strip()
    feedback = data.get("feedback", "").strip()
    instructions = data.get("instructions", "").strip()
    conversations = data.get("conversations", [])
    
    if not current_suggestion or not feedback:
        return jsonify({"success": False, "error": "Missing suggestion or feedback"}), 400
    
    try:
        # Build conversation context
        conv_text = "MULTI-PERSON CONVERSATION:\n"
        for idx, conv in enumerate(conversations, 1):
            participant = conv.get("participant", "Unknown")
            text = conv.get("translatedText") or conv.get("originalText", "")
            conv_text += f"\n{idx}. {participant}: {text}"
        
        llm = build_llm(get_llm_settings())
        if not llm:
            return jsonify({"success": False, "error": "LLM not configured"}), 503
        
        # Generate refined suggestion
        refine_prompt = f"""{conv_text}

ORIGINAL INSTRUCTIONS: {instructions}

PREVIOUS SUGGESTION: {current_suggestion}

USER FEEDBACK: {feedback}

Based on the user's feedback, please provide a REFINED suggestion that:
1. Takes the user's concerns into account
2. Maintains the core objective where appropriate
3. Addresses the specific points raised in the feedback
4. Is more practical or detailed than the previous suggestion

Please provide the refined suggestion with the same structure as before."""
        
        refined = llm.chat([
            {"role": "system", "content": "You are an AI assistant refining suggestions based on feedback."},
            {"role": "user", "content": refine_prompt}
        ])
        
        if not refined:
            return jsonify({"success": False, "error": "Failed to refine suggestion"}), 500
        
        logger.info(f"Refined multiperson suggestion based on user feedback")
        
        return jsonify({
            "success": True,
            "refinedSuggestion": refined.strip(),
            "feedback_considered": feedback
        }), 200
        
    except Exception as e:
        logger.error(f"Multiperson refinement error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@multiperson_bp.route("/multiperson-diarize", methods=["POST"])
@require_auth
def diarize_conversation():
    """
    Process audio with automatic speaker diarization.
    
    Form data:
        "audio": audio file (wav, mp3, etc.)
        "language": language code (english, igbo, hausa, yoruba)
    
    Returns:
        {
            "success": bool,
            "conversations": [
                {
                    "participant": "Speaker 1",
                    "originalText": "...",
                    "translatedText": "...",
                    "timestamp": "..."
                }
            ]
        }
    """
    ctx = current_user_context()
    if not (ctx.get('is_admin') or ctx.get('is_central_admin')):
        return jsonify({"success": False, "error": "Only admins can use this feature"}), 403
    
    try:
        # Get audio file
        if 'audio' not in request.files:
            return jsonify({"success": False, "error": "No audio file provided"}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"success": False, "error": "No audio file selected"}), 400
        
        language = request.form.get('language', 'english')
        
        # Get LLM
        llm = build_llm(get_llm_settings())
        if not llm:
            return jsonify({"success": False, "error": "LLM not configured"}), 503
        
        # Get user's audio settings to determine STT model preference
        from ..models import UserSettings
        user_audio_settings = {}
        stt_model = 'auto'  # Default to auto-detect
        
        # Allow passing stt_model via request (for flexibility)
        request_stt_model = request.form.get('sttModel', '').strip().lower() or request.args.get('sttModel', '').strip().lower()
        if request_stt_model and request_stt_model != 'auto':
            stt_model = request_stt_model
            logger.info(f"📊 Request override: Using {stt_model} for {language}")
        else:
            # Fall back to user's settings preference
            if ctx.get('user_id'):
                user_settings = UserSettings.query.filter_by(user_id=ctx.get('user_id')).first()
                if user_settings:
                    user_audio_settings = user_settings.get_audio_settings() or {}
                    user_stt = user_audio_settings.get('sttModel', '').strip().lower()
                    # Only override if user has explicitly chosen a service (not 'auto' or empty)
                    if user_stt and user_stt != 'auto':
                        stt_model = user_stt
                        logger.info(f"📊 User preference: Using {stt_model} for {language}")
        
        # Save temporary audio file
        import tempfile
        temp_dir = tempfile.gettempdir()
        
        # Determine file extension from content type or default to webm
        content_type = audio_file.content_type or 'audio/webm'
        ext_map = {
            'audio/wav': '.wav',
            'audio/webm': '.webm',
            'audio/mpeg': '.mp3',
            'audio/mp4': '.m4a',
            'audio/ogg': '.ogg',
        }
        file_ext = ext_map.get(content_type, '.webm')
        
        temp_audio_path = os.path.join(temp_dir, f"audio_{ctx.get('user_id')}_{os.urandom(4).hex()}{file_ext}")
        audio_file.save(temp_audio_path)
        
        logger.info(f"📁 Audio file saved: {temp_audio_path}")
        logger.info(f"   Content-Type: {content_type}")
        logger.info(f"   File extension: {file_ext}")
        
        # CRITICAL: Validate audio file was saved correctly
        if not os.path.exists(temp_audio_path):
            logger.error(f"❌ Audio file not saved: {temp_audio_path}")
            return jsonify({"success": False, "error": "Failed to save audio file"}), 500
        
        file_size = os.path.getsize(temp_audio_path)
        logger.info(f"   File size: {file_size} bytes")
        
        if file_size == 0:
            logger.error(f"❌ Audio file is empty (0 bytes) - no audio was recorded")
            return jsonify({"success": False, "error": "No audio was recorded. Please ensure microphone is working and you spoke clearly."}), 400
        
        if file_size < 1000:  # Less than 1KB
            logger.warning(f"⚠️  Audio file is very small ({file_size} bytes) - may contain insufficient audio")
        
        try:
            # Validate audio format - support WAV and WebM
            is_valid_audio = False
            audio_duration = 0
            
            if file_ext == '.wav':
                try:
                    import wave
                    with wave.open(temp_audio_path, 'rb') as wav_file:
                        frames = wav_file.getnframes()
                        rate = wav_file.getframerate()
                        channels = wav_file.getnchannels()
                        audio_duration = frames / float(rate) if rate > 0 else 0
                        logger.info(f"🎵 WAV Audio: {audio_duration:.2f}s, {rate}Hz, {channels}ch, {frames} frames")
                        is_valid_audio = True
                except wave.Error as e:
                    logger.warning(f"⚠️  WAV validation error: {e} - will attempt to process anyway")
                    is_valid_audio = True  # Let backend try to process
            
            elif file_ext == '.webm':
                try:
                    # For WebM, use ffprobe or just try to process
                    # We'll validate by attempting to use librosa
                    import librosa
                    try:
                        audio_data, sr = librosa.load(temp_audio_path, sr=16000, mono=True)
                        audio_duration = len(audio_data) / sr
                        logger.info(f"🎵 WebM Audio: {audio_duration:.2f}s, {sr}Hz")
                        is_valid_audio = True
                    except Exception as e:
                        logger.warning(f"⚠️  WebM validation with librosa failed: {e}")
                        is_valid_audio = True  # Still try to process
                except ImportError:
                    logger.warning(f"⚠️  librosa not available, skipping WebM validation")
                    is_valid_audio = True  # Assume valid
            
            else:
                # For other formats (MP3, MP4, OGG), assume valid
                logger.info(f"📁 Audio format: {file_ext}")
                is_valid_audio = True
            
            if not is_valid_audio:
                logger.error(f"❌ Invalid audio file format")
                return jsonify({"success": False, "error": "Invalid audio file format. Please use WAV, WebM, MP3, or MP4."}), 400
            
            if audio_duration > 0 and audio_duration < 0.3:
                logger.error(f"❌ Audio too short ({audio_duration:.2f}s) - need at least 0.3 seconds")
                return jsonify({"success": False, "error": f"Audio too short ({audio_duration:.2f}s). Please record for at least 1 second."}), 400
            
            # Attempt speech-to-text conversion with user's preferred STT model
            logger.info(f"🚀 Starting STT with language={language}, model={stt_model}")
            transcript = perform_speech_to_text(temp_audio_path, language, llm, stt_model=stt_model)
            
            if not transcript:
                logger.error("❌ Speech-to-text returned empty transcript - all STT services failed")
                return jsonify({"success": False, "error": "Failed to transcribe audio - all STT services failed. Check logs for details."}), 500
            
            logger.debug(f"Transcript (language={language}): {transcript[:100]}...")
            
            # Perform diarization with multiple strategies:
            # 1. ElevenLabs Scribe (best speaker identification)
            # 2. Pyannote Audio (accurate open-source)
            # 3. LLM-based pattern matching
            # 4. Simple heuristics
            # Pass both transcript and audio_path for comprehensive speaker detection
            conversations = perform_speaker_diarization(transcript, language, llm, audio_path=temp_audio_path)
            
            logger.info(f"Diarized conversation with {len(conversations)} detected segments")
            
            return jsonify({
                "success": True,
                "conversations": conversations
            }), 200
        
        finally:
            # Clean up temp file
            try:
                os.remove(temp_audio_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Diarization error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


def perform_speech_to_text(audio_path, language, llm, stt_model='auto'):
    """
    Convert audio file to text using the specified STT model.
    
    RECOMMENDED FLOW FOR NIGERIAN LANGUAGES:
    Google Cloud (if configured) → NaijaVox-2.0 (FREE, optimized for Igbo/Yoruba/Hausa) → ElevenLabs → Mock
    
    RECOMMENDED FLOW FOR ENGLISH:
    Google Cloud → OpenAI Whisper API → Mock
    
    Supports:
    - 'google': Google Cloud Speech-to-Text (BEST African language support if configured)
    - 'naijavox': NaijaVox-2.0 (FREE, BEST for Nigerian languages: Yoruba, Hausa, Igbo, Pidgin)
    - 'whisper': OpenAI Whisper API (supports ~99 languages but NOT Igbo/Yoruba/Hausa API codes)
    - 'elevenlabs': ElevenLabs Scribe API (premium, good African language support)
    - 'local': Local Whisper model (if configured)
    - 'auto': Auto-detect best available service (default)
    
    Args:
        audio_path: Path to audio file
        language: Language code (english, igbo, hausa, yoruba, pidgin)
        llm: LLM instance for fallback
        stt_model: Which STT model to use (default: 'auto')
    
    Returns:
        Transcribed text or None if all services fail
    """
    try:
        # Validate audio file exists and has content
        if not os.path.exists(audio_path):
            logger.error(f"❌ Audio file not found: {audio_path}")
            return None
        
        file_size = os.path.getsize(audio_path)
        if file_size == 0:
            logger.error(f"❌ Audio file is empty (0 bytes)")
            return None
        
        logger.debug(f"📁 Processing audio file: {audio_path} ({file_size} bytes)")
        
        # Map language codes to various formats
        language_lower = language.lower()
        language_map = {
            'english': {'google': 'en-US', 'whisper': 'en', 'elevenlabs': 'en-US', 'naijavox': 'nigerian_english'},
            'igbo': {'google': 'ig-NG', 'whisper': None, 'elevenlabs': 'ig', 'naijavox': 'igbo'},  # Note: Whisper API doesn't support 'ig'
            'hausa': {'google': 'ha-NG', 'whisper': None, 'elevenlabs': 'ha', 'naijavox': 'hausa'},  # Note: Whisper API doesn't support 'ha'
            'yoruba': {'google': 'yo-NG', 'whisper': None, 'elevenlabs': 'yo', 'naijavox': 'yoruba'},  # Note: Whisper API doesn't support 'yo'
            'pidgin': {'google': 'en-US', 'whisper': 'en', 'elevenlabs': 'en-US', 'naijavox': 'pidgin'},
        }
        
        lang_codes = language_map.get(language_lower, language_map['english'])
        is_nigerian_language = language_lower in ('igbo', 'hausa', 'yoruba', 'pidgin')
        
        # Auto-detect best available service with language-aware prioritization
        if stt_model == 'auto':
            if is_nigerian_language:
                # For Nigerian languages: Check what's available
                has_google_cloud = os.getenv('GOOGLE_CLOUD_STT_CREDENTIALS_PATH') or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                has_naijavox = True  # Always try NaijaVox (it's offline/free)
                
                # Prioritize: Google Cloud (best for African languages) → NaijaVox (free, optimized)
                if has_google_cloud:
                    stt_model = 'google'
                    logger.info(f"📊 Auto-detect: Google Cloud available - will use it for {language}")
                else:
                    stt_model = 'naijavox'
                    logger.info(f"📊 Auto-detect: Google Cloud not configured, using NaijaVox-2.0 for {language}")
            else:
                # For English: Google Cloud → Whisper
                has_google_cloud = os.getenv('GOOGLE_CLOUD_STT_CREDENTIALS_PATH') or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                has_whisper = os.getenv('OPENAI_API_KEY')
                
                if has_google_cloud:
                    stt_model = 'google'
                    logger.info(f"📊 Auto-detect: Google Cloud available - will use it for English")
                elif has_whisper:
                    stt_model = 'whisper'
                    logger.info(f"📊 Auto-detect: Whisper available for English")
                else:
                    stt_model = 'mock'
                    logger.warning(f"📊 Auto-detect: No STT service configured!")
        
        # Try requested STT service with intelligent fallback
        logger.info(f"\n{'='*60}")
        logger.info(f"🎯 STT Pipeline Started")
        logger.info(f"   Language: {language} (Nigerian: {is_nigerian_language})")
        logger.info(f"   File: {audio_path} ({file_size} bytes)")
        logger.info(f"   Model: {stt_model}")
        logger.info(f"{'='*60}")
        
        if stt_model == 'google':
            logger.info("1️⃣  Trying: Google Cloud Speech-to-Text...")
            try:
                transcript = _transcribe_with_google_cloud(audio_path, lang_codes.get('google', 'en-US'), language)
                if transcript:
                    logger.info(f"✅ SUCCESS: Google Cloud - {len(transcript)} chars")
                    return transcript
                logger.warning(f"❌ FAILED: Google Cloud - no transcript returned")
            except Exception as e:
                logger.error(f"❌ EXCEPTION in Google Cloud: {str(e)}", exc_info=True)
            
            logger.warning(f"   → Trying next service...")
            # Fall through to next service
            if is_nigerian_language:
                stt_model = 'naijavox'
            elif os.getenv('OPENAI_API_KEY'):
                stt_model = 'whisper'
            else:
                stt_model = 'mock'
        
        if stt_model == 'naijavox':
            logger.info("2️⃣  Trying: NaijaVox-2.0 (FREE, optimized for Nigerian languages)...")
            try:
                transcript = _transcribe_with_naijavox(audio_path, lang_codes.get('naijavox', language_lower), language)
                if transcript:
                    logger.info(f"✅ SUCCESS: NaijaVox-2.0 - {len(transcript)} chars")
                    return transcript
                logger.warning(f"❌ FAILED: NaijaVox - no transcript returned")
            except Exception as e:
                logger.error(f"❌ EXCEPTION in NaijaVox: {str(e)}", exc_info=True)
            
            logger.warning(f"   → Trying next service...")
            # Fall through to next service
            if os.getenv('ELEVENLABS_API_KEY'):
                stt_model = 'elevenlabs'
            elif os.getenv('OPENAI_API_KEY') and not is_nigerian_language:
                stt_model = 'whisper'
            else:
                stt_model = 'mock'
        
        if stt_model == 'whisper':
            # IMPORTANT: Only use Whisper for languages it actually supports
            whisper_code = lang_codes.get('whisper')
            if whisper_code is None:
                logger.warning(f"⏭️  SKIPPED: Whisper doesn't support '{language}' - trying next service...")
                if os.getenv('ELEVENLABS_API_KEY'):
                    stt_model = 'elevenlabs'
                else:
                    stt_model = 'mock'
            else:
                logger.info("3️⃣  Trying: OpenAI Whisper API...")
                try:
                    transcript = _transcribe_with_whisper(audio_path, whisper_code, language)
                    if transcript:
                        logger.info(f"✅ SUCCESS: Whisper - {len(transcript)} chars")
                        return transcript
                    logger.warning(f"❌ FAILED: Whisper - no transcript returned")
                except Exception as e:
                    logger.error(f"❌ EXCEPTION in Whisper: {str(e)}", exc_info=True)
                
                logger.warning(f"   → Trying next service...")
                # Fall through to next service
                if os.getenv('ELEVENLABS_API_KEY'):
                    stt_model = 'elevenlabs'
                else:
                    stt_model = 'mock'
        
        if stt_model == 'elevenlabs':
            logger.info("4️⃣  Trying: ElevenLabs Scribe...")
            try:
                elevenlabs_code = lang_codes.get('elevenlabs', lang_codes.get('google', 'en-US'))
                transcript = _transcribe_with_elevenlabs(audio_path, elevenlabs_code, language)
                if transcript:
                    logger.info(f"✅ SUCCESS: ElevenLabs - {len(transcript)} chars")
                    return transcript
                logger.warning(f"❌ FAILED: ElevenLabs - no transcript returned")
            except Exception as e:
                logger.error(f"❌ EXCEPTION in ElevenLabs: {str(e)}", exc_info=True)
            
            logger.warning(f"   → All STT services failed, returning error")
        
        if stt_model == 'local':
            logger.info("5️⃣  Trying: Local Whisper Model...")
            transcript = _transcribe_with_local_model(audio_path, lang_codes.get('whisper', 'en'), language)
            if transcript:
                logger.info(f"✅ SUCCESS: Local Model - {len(transcript)} chars")
                return transcript
            logger.warning(f"❌ FAILED: Local Model - falling back to mock...")
            stt_model = 'mock'
        
        # NO MOCK FALLBACK - Services must work with real STT
        logger.error(f"❌ ALL STT SERVICES FAILED for '{language}'")
        logger.error(f"   Required fixes:")
        logger.error(f"   1. For NaijaVox (FREE, African languages):")
        logger.error(f"      pip install transformers torch librosa")
        logger.error(f"   2. For Google Cloud (if configured):")
        logger.error(f"      Set GOOGLE_CLOUD_STT_CREDENTIALS_PATH in .env")
        logger.error(f"   3. For ElevenLabs:")
        logger.error(f"      Set ELEVENLABS_API_KEY in .env with 'audio_to_text_create' permission")
        logger.error(f"   4. For OpenAI Whisper (English only):")
        logger.error(f"      Set OPENAI_API_KEY in .env")
        return None  # No mock - force user to fix STT setup
        
    except Exception as e:
        logger.error(f"Speech-to-text error: {e}", exc_info=True)
        return None


def _transcribe_with_google_cloud(audio_path, language_code, language):
    """
    Transcribe audio using Google Cloud Speech-to-Text API.
    
    BEST SUPPORT FOR AFRICAN LANGUAGES:
    - Igbo (ig-NG): Native Nigerian Igbo
    - Yoruba (yo-NG): Native Nigerian Yoruba
    - Hausa (ha-NG): Native Nigerian Hausa
    - Plus 100+ other languages
    
    Args:
        audio_path: Path to audio file (WAV, MP3, FLAC, OGG, OPUS, WebM)
        language_code: BCP-47 language code (e.g., 'ig-NG', 'yo-NG', 'ha-NG')
        language: Display name for logging
    
    Returns:
        Transcribed text or None if failed
    
    Setup:
    1. Create Google Cloud project: https://console.cloud.google.com
    2. Enable Speech-to-Text API
    3. Create service account: IAM → Service Accounts
    4. Download JSON key
    5. Set GOOGLE_CLOUD_STT_CREDENTIALS_PATH in .env
    
    Or use GOOGLE_APPLICATION_CREDENTIALS environment variable.
    """
    try:
        # Try to import Google Cloud Speech library
        try:
            from google.cloud import speech_v1
        except ImportError:
            logger.debug("google-cloud-speech not installed. Install with: pip install google-cloud-speech")
            return None
        
        # Check if credentials are configured
        credentials_path = os.getenv('GOOGLE_CLOUD_STT_CREDENTIALS_PATH')
        if credentials_path and os.path.exists(credentials_path):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            logger.debug("GOOGLE_APPLICATION_CREDENTIALS not configured")
            return None
        
        # Create client
        client = speech_v1.SpeechClient()
        
        # Detect audio format from file extension
        file_ext = os.path.splitext(audio_path)[1].lower()
        logger.debug(f"🎵 Google Cloud: Detected file extension: {file_ext}")
        
        # Handle WebM - need to convert to WAV for Google Cloud
        if file_ext == '.webm':
            logger.debug(f"🔄 Converting WebM to WAV for Google Cloud compatibility...")
            try:
                import librosa
                
                # Load WebM with librosa
                audio_data, sr = librosa.load(audio_path, sr=16000, mono=True)
                logger.debug(f"   Loaded WebM: {len(audio_data)} samples at {sr}Hz")
                
                # Save as temporary WAV file using scipy or wave module
                import tempfile
                import wave
                import numpy as np
                
                temp_dir = tempfile.gettempdir()
                wav_path = os.path.join(temp_dir, f"converted_{os.urandom(4).hex()}.wav")
                
                # Convert float audio to 16-bit PCM
                audio_int16 = np.int16(audio_data / np.max(np.abs(audio_data)) * 32767)
                
                # Write WAV file
                with wave.open(wav_path, 'w') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(sr)  # Sample rate
                    wav_file.writeframes(audio_int16.tobytes())
                
                logger.debug(f"   Converted to WAV: {wav_path}")
                
                audio_path = wav_path
                file_ext = '.wav'
            except Exception as e:
                logger.warning(f"⚠️  WebM conversion failed: {e} - proceeding with NaijaVox instead")
                # Don't fail here - let NaijaVox handle WebM directly via librosa
        
        # Detect audio format
        audio_format = speech_v1.RecognitionConfig.AudioEncoding.LINEAR16
        
        if file_ext == '.mp3':
            audio_format = speech_v1.RecognitionConfig.AudioEncoding.MP3
        elif file_ext == '.flac':
            audio_format = speech_v1.RecognitionConfig.AudioEncoding.FLAC
        elif file_ext == '.ogg':
            audio_format = speech_v1.RecognitionConfig.AudioEncoding.OGG_OPUS
        elif file_ext == '.wav':
            audio_format = speech_v1.RecognitionConfig.AudioEncoding.LINEAR16
        
        logger.debug(f"   Audio format: {audio_format}")
        
        # Read audio file
        with open(audio_path, 'rb') as audio_file:
            content = audio_file.read()
        
        logger.debug(f"   Audio size: {len(content)} bytes")
        
        audio = speech_v1.RecognitionAudio(content=content)
        
        # Configure recognition request
        config = speech_v1.RecognitionConfig(
            encoding=audio_format,
            language_code=language_code,
            sample_rate_hertz=16000,
            audio_channel_count=1,
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,
            use_enhanced=True,
            model='latest_long',
        )
        
        # Perform recognition
        logger.info(f"📤 Sending {len(content)} bytes to Google Cloud Speech-to-Text ({language_code})")
        response = client.recognize(config=config, audio=audio)
        
        # Extract transcript
        transcript_parts = []
        for result in response.results:
            for alternative in result.alternatives:
                transcript_parts.append(alternative.transcript)
        
        transcript = ' '.join(transcript_parts).strip()
        
        if transcript:
            logger.info(f"✅ Google Cloud success: {len(transcript)} chars for {language}")
            return transcript
        else:
            logger.warning(f"❌ Google Cloud returned empty transcript for {language}")
            return None
        
    except Exception as e:
        logger.warning(f"❌ Google Cloud STT error for {language}: {e}", exc_info=True)
        return None


def _transcribe_with_whisper(audio_path, language_code, language):
    """
    Transcribe audio using OpenAI Whisper API.
    
    Fallback when Google Cloud is not available.
    Supports ~99 languages but with varying accuracy.
    African languages work but with less accuracy than Google Cloud.
    
    Args:
        audio_path: Path to audio file
        language_code: ISO 639-1 language code (en, ig, ha, yo, etc.)
        language: Display name for logging
    
    Returns:
        Transcribed text or None if failed
    """
    try:
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            logger.debug("OPENAI_API_KEY not configured")
            return None
        
        try:
            import openai
        except ImportError:
            logger.debug("openai library not installed. Install with: pip install openai")
            return None
        
        client = openai.OpenAI(api_key=openai_api_key)
        
        # Determine file MIME type
        file_ext = os.path.splitext(audio_path)[1].lower()
        mime_types = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
            '.flac': 'audio/flac',
            '.m4a': 'audio/mp4',
        }
        mime_type = mime_types.get(file_ext, 'audio/wav')
        
        logger.debug(f"Sending audio to Whisper API ({language_code})")
        
        with open(audio_path, 'rb') as audio:
            transcript_obj = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
                language=language_code,
                temperature=0.0,  # For consistent transcription
            )
        
        transcript = transcript_obj.text.strip()
        
        if transcript:
            logger.info(f"Whisper transcription successful for {language}: {len(transcript)} chars")
            return transcript
        else:
            logger.warning(f"Whisper returned empty transcript for {language}")
            return None
            
    except Exception as e:
        logger.warning(f"Whisper transcription error for {language}: {e}")
        return None


def _transcribe_with_elevenlabs(audio_path, lang_code, language):
    """
    Transcribe audio using ElevenLabs Scribe API.
    
    Supports multilingual transcription with high accuracy for African languages.
    Requires ELEVENLABS_API_KEY environment variable.
    
    Returns:
        Transcribed text or None if failed/not configured
    
    Setup:
    1. Create ElevenLabs account at https://elevenlabs.io
    2. Get API key from settings/dashboard
    3. Set ELEVENLABS_API_KEY in .env
    
    Features:
    - Native African language support (Igbo, Hausa, Yoruba, Swahili, etc.)
    - High accuracy for regional accents
    - Automatic speaker diarization
    - Emotion and intent detection
    
    Endpoint: https://api.elevenlabs.io/v1/audio-to-text
    Docs: https://elevenlabs.io/docs/audio-to-text
    """
    try:
        elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
        if not elevenlabs_api_key:
            logger.debug("ELEVENLABS_API_KEY not configured, skipping ElevenLabs")
            return None
        
        try:
            import requests
        except ImportError:
            logger.debug("requests library not available for ElevenLabs API")
            return None
        
        logger.debug(f"Sending audio to ElevenLabs Scribe API ({lang_code})")
        
        with open(audio_path, 'rb') as audio_file:
            files = {'audio': audio_file}
            headers = {'xi-api-key': elevenlabs_api_key}
            
            response = requests.post(
                'https://api.elevenlabs.io/v1/audio-to-text',
                files=files,
                headers=headers,
                data={'language': lang_code},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                transcript = data.get('text', '').strip()
                if transcript:
                    logger.info(f"ElevenLabs transcription successful for {language}: {len(transcript)} chars")
                    return transcript
                else:
                    logger.warning(f"ElevenLabs returned empty response for {language}")
                    return None
            else:
                logger.warning(f"ElevenLabs API error ({response.status_code}): {response.text}")
                return None
        
    except Exception as e:
        logger.warning(f"ElevenLabs transcription error: {e}")
        return None


def _transcribe_with_local_model(audio_path, lang_code, language):
    """
    Transcribe audio using local/regional speech-to-text models.
    
    Supports:
    - Local Whisper: https://github.com/openai/whisper
    - N-ATLaS-LLM: African language models https://github.com/uonlrnr/n-atlas-llm
    - Awarri: Yoruba-optimized https://huggingface.co/
    
    Returns:
        Transcribed text or None if failed/not configured
    
    Setup (Local Whisper - Recommended):
    1. Install: pip install openai-whisper
    2. Set LOCAL_STT_MODEL_PATH=/path/to/model in .env
    3. Choose model size: tiny, base, small, medium, large
    
    Note: Large model provides best accuracy but requires more resources.
    For African languages, use 'medium' or 'large' model.
    
    Models support:
    - Igbo: Medium-to-large model works well
    - Yoruba: Large model recommended  
    - Hausa: Medium-to-large model works well
    """
    try:
        # Check if local model is configured
        local_model_path = os.getenv('LOCAL_STT_MODEL_PATH')
        if not local_model_path:
            logger.debug("LOCAL_STT_MODEL_PATH not configured, skipping local STT")
            return None
        
        # Try to import Whisper
        try:
            import whisper
        except ImportError:
            logger.debug("openai-whisper not installed. Install with: pip install openai-whisper")
            return None
        
        # Load model if not already cached
        if not hasattr(_transcribe_with_local_model, 'model_cache'):
            _transcribe_with_local_model.model_cache = {}
        
        cache_key = local_model_path
        if cache_key not in _transcribe_with_local_model.model_cache:
            logger.info(f"Loading local Whisper model from: {local_model_path}")
            try:
                model = whisper.load_model(local_model_path)
                _transcribe_with_local_model.model_cache[cache_key] = model
            except Exception as e:
                logger.warning(f"Failed to load local Whisper model: {e}")
                return None
        
        model = _transcribe_with_local_model.model_cache[cache_key]
        
        logger.debug(f"Transcribing with local Whisper model ({lang_code})")
        
        # Transcribe with local model
        result = model.transcribe(
            audio_path,
            language=lang_code,
            verbose=False,
            temperature=0.0
        )
        
        transcript = result.get('text', '').strip()
        
        if transcript:
            logger.info(f"Local Whisper transcription successful for {language}: {len(transcript)} chars")
            return transcript
        else:
            logger.warning(f"Local Whisper returned empty transcript for {language}")
            return None
        
    except Exception as e:
        logger.warning(f"Local model transcription error: {e}")
        return None


def _transcribe_with_naijavox(audio_path, language, language_display):
    """Transcribe using NaijaVox-2.0 model for Nigerian languages."""
    try:
        logger.debug(f"NaijaVox: Loading dependencies...")
        try:
            from transformers import WhisperForConditionalGeneration, WhisperProcessor
            import torch
            import librosa
            logger.debug(f"✅ NaijaVox dependencies loaded successfully")
        except ImportError as e:
            logger.error(f"❌ NaijaVox dependencies missing: {e}")
            logger.error(f"   Install with: pip install transformers torch librosa torchaudio")
            return None
        
        # Validate audio file
        if not os.path.exists(audio_path):
            logger.error(f"❌ NaijaVox: Audio file not found: {audio_path}")
            return None
        
        file_size = os.path.getsize(audio_path)
        logger.debug(f"📁 NaijaVox: Audio file size: {file_size} bytes")
        
        MODEL_ID = "Axiveri/NaijaVox-2.0"
        LANG_TOKENS = {
            "yoruba": "<|yo|>",
            "hausa": "<|ha|>",
            "igbo": "<|ig|>",
            "pidgin": "<|pcm|>",
            "nigerian_english": "<|en|>",
        }
        
        language_lower = language.lower()
        if language_lower not in LANG_TOKENS:
            logger.error(f"❌ NaijaVox: Unsupported language '{language_lower}'")
            logger.error(f"   Supported: {list(LANG_TOKENS.keys())}")
            return None
        
        logger.info(f"🚀 NaijaVox-2.0: Initializing for {language_display}...")
        
        # Determine device: resolve 'auto' to 'cuda' or 'cpu'
        device_env = os.getenv('NAIJAVOX_DEVICE', 'auto').lower()
        if device_env == 'auto':
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            device = device_env
        
        logger.info(f"   Device: {device}")
        
        dtype_str = os.getenv('NAIJAVOX_TORCH_DTYPE', 'float16' if device == 'cuda' else 'float32')
        torch_dtype = torch.float16 if dtype_str == 'float16' else torch.float32
        logger.info(f"   Dtype: {dtype_str}")
        
        # Cache the model
        if not hasattr(_transcribe_with_naijavox, 'model_cache'):
            _transcribe_with_naijavox.model_cache = {}
        
        cache_key = f"{MODEL_ID}_{device}"
        if cache_key not in _transcribe_with_naijavox.model_cache:
            logger.info(f"   ⬇️  Downloading model (first time, ~2.5GB)...")
            try:
                model = WhisperForConditionalGeneration.from_pretrained(
                    MODEL_ID,
                    torch_dtype=torch_dtype,
                    low_cpu_mem_usage=True,
                    use_safetensors=True,
                )
                model.to(device)
                processor = WhisperProcessor.from_pretrained(MODEL_ID)
                _transcribe_with_naijavox.model_cache[cache_key] = (model, processor, device)
                logger.info(f"✅ NaijaVox-2.0 model loaded successfully")
            except Exception as e:
                logger.error(f"❌ NaijaVox: Failed to load model: {e}")
                return None
        else:
            logger.debug(f"♻️  Using cached NaijaVox-2.0 model")
        
        model, processor, device = _transcribe_with_naijavox.model_cache[cache_key]
        
        # Load audio
        logger.debug(f"🎵 Loading audio from {audio_path}...")
        try:
            audio_array, sampling_rate = librosa.load(audio_path, sr=16000)
            logger.debug(f"✅ Audio loaded: {len(audio_array)} samples at {sampling_rate}Hz")
            
            if len(audio_array) == 0:
                logger.error(f"❌ NaijaVox: Audio array is empty - audio file may be corrupted")
                return None
        except Exception as e:
            logger.error(f"❌ NaijaVox: Failed to load audio: {e}")
            return None
        
        # Prepare language tokens
        logger.debug(f"🎯 Preparing language tokens for {language_lower}...")
        try:
            vocab = processor.tokenizer.get_vocab()
            lang_id = vocab[LANG_TOKENS[language_lower]]
            start = vocab["<|startoftranscript|>"]
            trans = vocab["<|transcribe|>"]
            nots = vocab["<|notimestamps|>"]
            decoder_input_ids = torch.tensor([[start, lang_id, trans, nots]]).to(device)
            logger.debug(f"✅ Language tokens prepared")
        except Exception as e:
            logger.error(f"❌ NaijaVox: Failed to prepare language tokens: {e}")
            return None
        
        # Process audio
        logger.debug(f"🔊 Preprocessing audio...")
        try:
            inputs = processor.feature_extractor(
                audio_array,
                sampling_rate=sampling_rate,
                return_tensors="pt"
            ).input_features.to(device)
            logger.debug(f"✅ Audio preprocessed: {inputs.shape}")
        except Exception as e:
            logger.error(f"❌ NaijaVox: Failed to preprocess audio: {e}")
            return None
        
        # Generate transcription
        logger.debug(f"💬 Running NaijaVox-2.0 inference...")
        try:
            with torch.no_grad():
                generated = model.generate(
                    input_features=inputs,
                    decoder_input_ids=decoder_input_ids,
                    max_new_tokens=448,
                )
            logger.debug(f"✅ Inference complete")
        except Exception as e:
            logger.error(f"❌ NaijaVox: Inference failed: {e}")
            return None
        
        # Decode to text
        logger.debug(f"📝 Decoding output to text...")
        try:
            transcript = processor.tokenizer.decode(generated[0], skip_special_tokens=True).strip()
            logger.debug(f"✅ Decoded: {transcript[:100]}...")
        except Exception as e:
            logger.error(f"❌ NaijaVox: Decoding failed: {e}")
            return None
        
        if transcript:
            logger.info(f"✅ NaijaVox-2.0 success: {len(transcript)} chars for {language_display}")
            return transcript
        else:
            logger.warning(f"❌ NaijaVox-2.0: Empty transcript returned")
            return None
            
    except Exception as e:
        logger.error(f"❌ NaijaVox-2.0 unexpected error: {e}", exc_info=True)
        return None




def generate_mock_transcript(audio_path):
    """
    Generate a realistic mock transcript for testing when real speech-to-text is unavailable.
    In production, this should be replaced with actual speech-to-text.
    
    Creates multi-speaker conversations for better testing of diarization.
    """
    try:
        import wave
        with wave.open(audio_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate) if rate > 0 else 0
        
        logger.info(f"Generating mock transcript for audio of duration {duration:.1f}s")
        
        # Different mock transcripts based on duration
        if duration < 3:
            return "Speaker 1: Hello, how are you? Speaker 2: I'm doing well, thanks for asking."
        elif duration < 10:
            return """Speaker 1: Good morning everyone, thanks for joining the meeting.
Speaker 2: Thanks for organizing this. What are we discussing today?
Speaker 1: We need to review the project timeline and discuss resource allocation.
Speaker 2: That sounds important. Do we have the Q4 budget figures?
Speaker 1: Yes, I'll share those in a moment."""
        else:
            return """Speaker 1: Hello everyone, I wanted to start by discussing our quarterly objectives.
Speaker 2: Great, I've been looking forward to this discussion. What are the key areas?
Speaker 1: First, we need to improve our code quality and testing coverage.
Speaker 2: I agree. We should also focus on documentation.
Speaker 3: What about infrastructure improvements?
Speaker 1: Excellent point. Infrastructure modernization is crucial.
Speaker 3: We need to migrate the legacy database systems.
Speaker 2: How long will that take?
Speaker 3: Probably three to four months with proper planning.
Speaker 1: Let's allocate that as one of our main Q4 initiatives."""
    except Exception as e:
        logger.warning(f"Failed to read WAV file for mock transcript: {e}")
        return "Speaker 1: This is a test conversation. Speaker 2: Yes, let's proceed with the discussion."


def perform_speaker_diarization(original_text, source_language, llm):
    """
    Use LLM to identify speakers and diarize the conversation.
    
    Implements Segment-Level Translation (MVP Approach):
    - Performs diarization on the original language text
    - Translates each diarized segment individually to English
    - Preserves source language in originalText and provides translation in translatedText
    
    Args:
        original_text: Transcript in source language
        source_language: Language code (english, igbo, hausa, yoruba)
        llm: LLM instance for diarization
    
    Returns a list of {participant, originalText, translatedText, timestamp} dicts.
    """
    try:
        # Ensure we have valid text to diarize
        if not original_text or not original_text.strip():
            duration = frames / float(rate) if rate > 0 else 0
        
        logger.info(f"Generating mock transcript for audio of duration {duration:.1f}s")
        
        # Different mock transcripts based on duration
        if duration < 3:
            return "Speaker 1: Hello, how are you? Speaker 2: I'm doing well, thanks for asking."
        elif duration < 10:
            return """Speaker 1: Good morning everyone, thanks for joining the meeting.
Speaker 2: Thanks for organizing this. What are we discussing today?
Speaker 1: We need to review the project timeline and discuss resource allocation.
Speaker 2: That sounds important. Do we have the Q4 budget figures?
Speaker 1: Yes, I'll share those in a moment."""
        else:
            return """Speaker 1: Hello everyone, I wanted to start by discussing our quarterly objectives.
Speaker 2: Great, I've been looking forward to this discussion. What are the key areas?
Speaker 1: First, we need to improve our code quality and testing coverage.
Speaker 2: I agree. We should also focus on documentation.
Speaker 3: What about infrastructure improvements?
Speaker 1: Excellent point. Infrastructure modernization is crucial.
Speaker 3: We need to migrate the legacy database systems.
Speaker 2: How long will that take?
Speaker 3: Probably three to four months with proper planning.
Speaker 1: Let's allocate that as one of our main Q4 initiatives."""
    except Exception as e:
        logger.warning(f"Failed to read WAV file for mock transcript: {e}")
        return "Speaker 1: This is a test conversation. Speaker 2: Yes, let's proceed with the discussion."


def perform_speaker_diarization(original_text, source_language, llm, audio_path=None):
    """
    Perform speaker diarization using multiple strategies in order:
    1. ElevenLabs Scribe API (premium, includes speaker diarization)
    2. Pyannote Audio (open-source, accurate speaker detection)
    3. LLM-based pattern matching (fallback)
    4. Simple heuristic fallback
    
    Implements Segment-Level Translation:
    - Preserves source language in originalText
    - Provides translation in translatedText
    - Identifies multiple speakers accurately
    
    Args:
        original_text: Transcript in source language
        source_language: Language code (english, igbo, hausa, yoruba)
        llm: LLM instance for fallback
        audio_path: Path to audio file (optional, for ElevenLabs/Pyannote)
    
    Returns:
        List of {participant, originalText, translatedText, timestamp} dicts
    """
    try:
        # Ensure we have valid text to diarize
        if not original_text or not original_text.strip():
            logger.warning("Empty transcript for diarization")
            return fallback_single_speaker(original_text or "No transcript available")
        
        segments = None
        
        # Strategy 1: Try ElevenLabs Scribe API (if audio path provided)
        if audio_path and os.path.exists(audio_path):
            logger.info("Attempting ElevenLabs Scribe diarization...")
            segments = _diarize_with_elevenlabs_scribe(audio_path, source_language)
            if segments:
                logger.info(f"✓ ElevenLabs diarization successful: {len(segments)} speakers")
                return _convert_segments_to_conversations(segments, source_language)
        
        # Strategy 2: Try Pyannote Audio (if audio path provided)
        if audio_path and os.path.exists(audio_path):
            logger.info("Attempting Pyannote Audio diarization...")
            segments = _diarize_with_pyannote(audio_path, original_text)
            if segments:
                logger.info(f"✓ Pyannote diarization successful: {len(segments)} speakers")
                return _convert_segments_to_conversations(segments, source_language)
        
        # Strategy 3: Use LLM to identify speaker patterns
        logger.info("Attempting LLM-based diarization...")
        segments = _diarize_with_llm(original_text, llm)
        if segments:
            logger.info(f"✓ LLM diarization successful: {len(segments)} speakers")
            return _convert_segments_to_conversations(segments, source_language)
        
        # Strategy 4: Use simple heuristic fallback
        logger.info("Using heuristic-based diarization...")
        segments = fallback_diarization(original_text)
        if segments:
            logger.info(f"✓ Heuristic diarization found: {len(segments)} speakers")
            return _convert_segments_to_conversations(segments, source_language)
        
        # Ultimate fallback
        logger.error("All diarization methods failed, returning single speaker")
        return fallback_single_speaker(original_text)
        
    except Exception as e:
        logger.error(f"Diarization error: {e}", exc_info=True)
        return fallback_single_speaker(original_text)


def _diarize_with_elevenlabs_scribe(audio_path, source_language):
    """
    Use ElevenLabs Scribe API for speaker diarization.
    Scribe includes automatic speaker identification and diarization.
    
    Requires: ELEVENLABS_API_KEY with Scribe access
    """
    try:
        elevenlabs_key = os.getenv('ELEVENLABS_API_KEY', '').strip()
        if not elevenlabs_key:
            logger.debug("ElevenLabs API key not configured")
            return None
        
        import requests
        
        # ElevenLabs Scribe endpoint
        url = "https://api.elevenlabs.io/v1/scribe"
        
        headers = {
            "xi-api-key": elevenlabs_key
        }
        
        # Read audio file
        with open(audio_path, 'rb') as f:
            files = {'audio': f}
            
            # Send to ElevenLabs Scribe
            response = requests.post(
                url,
                headers=headers,
                files=files,
                data={"language": source_language},
                timeout=30
            )
        
        if response.status_code != 200:
            logger.warning(f"ElevenLabs Scribe error: HTTP {response.status_code}")
            return None
        
        data = response.json()
        
        # Extract segments with speaker info
        segments = []
        if 'segments' in data:
            for seg in data['segments']:
                if seg.get('text', '').strip():
                    segments.append({
                        'speaker': f"Speaker {seg.get('speaker_id', 1)}",
                        'text': seg.get('text', '')
                    })
        
        return segments if segments else None
        
    except ImportError:
        logger.debug("requests library not available for ElevenLabs")
        return None
    except Exception as e:
        logger.debug(f"ElevenLabs Scribe failed: {str(e)[:100]}")
        return None


def _diarize_with_pyannote(audio_path, original_text):
    """
    Use Pyannote Audio for speaker diarization.
    Open-source, no API key needed.
    
    Requires: pip install pyannote.audio
    """
    try:
        from pyannote.audio import Pipeline
        import torch
        
        logger.info("Loading Pyannote Audio pipeline...")
        
        # Use pretrained pipeline (requires huggingface token)
        # Or use a simpler approach
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=os.getenv('HUGGINGFACE_TOKEN', '')
        )
        
        # Run diarization
        logger.info(f"Running Pyannote diarization on {audio_path}...")
        diarization = pipeline(audio_path)
        
        # Extract speaker turns with text
        segments = []
        speaker_texts = {}
        
        # Map diarization results to text segments
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speaker_id = speaker.split('_')[0] if '_' in speaker else speaker
            speaker_name = f"Speaker {int(speaker_id) + 1}" if speaker_id.isdigit() else f"Speaker {speaker}"
            
            if speaker_name not in speaker_texts:
                speaker_texts[speaker_name] = []
            speaker_texts[speaker_name].append((turn.start, turn.end))
        
        # Split original text into sentences and assign to speakers
        import re
        sentences = re.split(r'(?<=[.!?])\s+', original_text.strip())
        
        # Simple assignment: alternate speakers based on text length
        if speaker_texts and sentences:
            speakers = list(speaker_texts.keys())
            for i, sentence in enumerate(sentences):
                if sentence.strip():
                    speaker = speakers[i % len(speakers)]
                    segments.append({
                        'speaker': speaker,
                        'text': sentence.strip()
                    })
        
        return segments if segments else None
        
    except ImportError:
        logger.debug("Pyannote not installed. Install with: pip install pyannote.audio")
        return None
    except Exception as e:
        logger.debug(f"Pyannote diarization failed: {str(e)[:100]}")
        return None


def _diarize_with_llm(original_text, llm):
    """
    Use LLM to identify speaker patterns and diarize text.
    Works best with text that already has speaker labels.
    """
    try:
        if not llm:
            return None
        
        diarize_prompt = f"""Analyze the following transcript and identify all distinct speakers.
Extract each speaker's statements separately.

Transcript:
{original_text}

For EACH different speaker, provide:
- speaker: "Speaker 1", "Speaker 2", etc. (or actual names if mentioned)
- text: What they said (complete sentences/phrases)

Return ONLY a valid JSON array. No markdown, no extra text.
Example: [
  {{"speaker": "Speaker 1", "text": "Hello everyone"}},
  {{"speaker": "Speaker 2", "text": "Hi, how are you?"}}
]"""
        
        response = llm.chat([
            {"role": "system", "content": "Extract speakers and their statements. Return ONLY valid JSON array."},
            {"role": "user", "content": diarize_prompt}
        ])
        
        if not response or not response.strip():
            logger.debug("LLM returned empty response for diarization")
            return None
        
        # Parse JSON response
        try:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
                cleaned = cleaned.strip()
            
            parsed = json.loads(cleaned)
            segments = parsed if isinstance(parsed, list) else [parsed]
            
            # Validate and count speakers
            speaker_count = len(set(s.get('speaker') for s in segments if isinstance(s, dict)))
            logger.info(f"LLM identified {speaker_count} speaker(s)")
            
            return segments if segments else None
            
        except json.JSONDecodeError as e:
            logger.debug(f"Failed to parse LLM response: {e}")
            return None
        
    except Exception as e:
        logger.debug(f"LLM diarization failed: {str(e)[:100]}")
        return None


def _convert_segments_to_conversations(segments, source_language):
    """
    Convert diarization segments to conversation format.
    
    IMPORTANT: NO AUTOMATIC TRANSLATION
    - Real-time display preserves ORIGINAL LANGUAGE
    - Translation to English happens ONLY if explicitly requested via /translate-statement endpoint
    - User sees text in the language they spoke
    """
    try:
        conversations = []
        timestamp_counter = 0
        
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            
            speaker = segment.get('speaker', f'Speaker {timestamp_counter + 1}')
            original_segment = segment.get('text', '').strip()
            
            if not original_segment:
                continue
            
            conversations.append({
                "participant": speaker,
                "originalText": original_segment,
                "language": source_language,  # Track source language for optional translation
                "translatedText": None,  # No auto-translation - user sees original language
                "timestamp": f"{timestamp_counter:02d}:00"
            })
            timestamp_counter += 1
        
        logger.info(f"✅ Converted {len(conversations)} segments to conversation format (NO TRANSLATION) - {source_language} preserved")
        return conversations if conversations else None
        
    except Exception as e:
        logger.error(f"Error converting segments to conversations: {e}")
        return None


def fallback_diarization(text):
    """Simple fallback diarization by splitting on common patterns."""
    if not text or not text.strip():
        return []
    
    segments = []
    speaker_num = 1
    
    # Try to split on patterns like "Speaker 1:" or "Person 1:"
    import re
    parts = re.split(r'(?:Speaker|Person|Participant)\s+\d+:', text)
    
    for part in parts:
        if part.strip():
            segments.append({
                "speaker": f"Speaker {speaker_num}",
                "text": part.strip()
            })
            speaker_num += 1
    
    # If no speaker pattern found, split by sentences or return as single
    if not segments:
        # Try splitting by common sentence endings
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for i, sentence in enumerate(sentences):
            if sentence.strip():
                segments.append({
                    "speaker": f"Speaker {(i % 2) + 1}",  # Alternate between Speaker 1 and 2
                    "text": sentence.strip()
                })
        
        # If still no segments, return as single speaker
        if not segments:
            segments = [{"speaker": "Speaker 1", "text": text}]
    
    return segments


def fallback_single_speaker(text):
    """Return text as single speaker when diarization fails."""
    if not text:
        text = "No transcript available"
    
    return [{
        "participant": "Speaker 1",
        "originalText": text,
        "translatedText": text,
        "timestamp": "00:00"
    }]


@multiperson_bp.route("/translate-statement", methods=["POST"])
@require_auth
def translate_statement():
    """
    Translate a single statement from one language to another.
    
    Request body:
    {
        "text": "Text to translate",
        "sourceLanguage": "igbo|yoruba|hausa|pidgin|english",
        "targetLanguage": "igbo|yoruba|hausa|pidgin|english" (optional, default: english)
    }
    
    Returns:
    {
        "success": true/false,
        "original": "Original text",
        "translated": "Translated text",
        "sourceLanguage": "igbo",
        "targetLanguage": "english"
    }
    """
    ctx = current_user_context()
    if not ctx:
        return jsonify({"success": False, "error": "Authentication required"}), 401
    
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    source_lang = (data.get("sourceLanguage") or "").strip().lower()
    target_lang = (data.get("targetLanguage") or "english").strip().lower()
    
    if not text:
        return jsonify({"success": False, "error": "Missing text to translate"}), 400
    
    if not source_lang:
        return jsonify({"success": False, "error": "Missing sourceLanguage"}), 400
    
    try:
        from ..translation import translate_to_english, translate
        
        # Translate statement
        if target_lang == 'english' or source_lang == 'english':
            if source_lang != 'english':
                # Translate from source to English
                translated = translate_to_english(text, source_lang)
                logger.info(f"Translated {source_lang} → english: {len(text)} → {len(translated)} chars")
            elif target_lang != 'english':
                # Translate from English to target
                translated = translate(text, 'english', target_lang)
                logger.info(f"Translated english → {target_lang}: {len(text)} → {len(translated)} chars")
            else:
                # No translation needed
                translated = text
        else:
            # Translate from source to target (via English)
            translated_to_en = translate_to_english(text, source_lang)
            translated = translate(translated_to_en, 'english', target_lang)
            logger.info(f"Translated {source_lang} → {target_lang} (via english)")
        
        return jsonify({
            "success": True,
            "original": text,
            "translated": translated,
            "sourceLanguage": source_lang,
            "targetLanguage": target_lang
        }), 200
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return jsonify({
            "success": False,
            "error": f"Translation failed: {str(e)}"
        }), 500


@multiperson_bp.route("/translate-conversation", methods=["POST"])
@require_auth
def translate_conversation():
    """
    Translate an entire multi-person conversation to English (post-processing).
    
    Called AFTER recording is complete to optionally translate all segments.
    This is SEPARATE from real-time transcription to ensure no latency impact.
    
    Request body:
    {
        "conversations": [
            {"participant": "Speaker 1", "originalText": "Kedu?", "language": "igbo"},
            {"participant": "Speaker 2", "originalText": "Obu mma", "language": "igbo"}
        ],
        "sourceLanguage": "igbo"
    }
    
    Returns:
    {
        "success": true/false,
        "conversations": [
            {
                "participant": "Speaker 1",
                "originalText": "Kedu?",
                "translatedText": "Hello?",
                "language": "igbo"
            },
            ...
        ]
    }
    """
    ctx = current_user_context()
    if not ctx:
        return jsonify({"success": False, "error": "Authentication required"}), 401
    
    data = request.get_json(silent=True) or {}
    conversations = data.get("conversations", [])
    source_language = (data.get("sourceLanguage") or "").strip().lower()
    
    if not conversations:
        return jsonify({"success": False, "error": "Missing conversations"}), 400
    
    if not source_language:
        return jsonify({"success": False, "error": "Missing sourceLanguage"}), 400
    
    # If already English, no translation needed
    if source_language == 'english':
        return jsonify({
            "success": True,
            "conversations": conversations,
            "message": "No translation needed (already English)"
        }), 200
    
    try:
        from ..translation import translate_to_english
        
        translated_conversations = []
        for conv in conversations:
            if not isinstance(conv, dict):
                continue
            
            original_text = conv.get("originalText", "").strip()
            if not original_text:
                translated_conversations.append(conv)
                continue
            
            try:
                translated_text = translate_to_english(original_text, source_language)
            except Exception as e:
                logger.warning(f"Translation failed for segment: {e}")
                translated_text = original_text  # Keep original if translation fails
            
            translated_conv = {
                **conv,
                "translatedText": translated_text
            }
            translated_conversations.append(translated_conv)
        
        logger.info(f"✅ Translated {len(translated_conversations)} conversation segments from {source_language} to english")
        
        return jsonify({
            "success": True,
            "conversations": translated_conversations,
            "sourceLanguage": source_language,
            "targetLanguage": "english"
        }), 200
        
    except Exception as e:
        logger.error(f"Conversation translation error: {e}")
        return jsonify({
            "success": False,
            "error": f"Translation failed: {str(e)}"
        }), 500


@multiperson_bp.route("/train-user-voice", methods=["POST"])
@require_auth
def train_user_voice():
    """
    Enroll user voice samples for speaker identification in multi-person conversations.
    
    ⚠️ IMPORTANT: This trains speaker identification, NOT AI content understanding.
    See docs/VOICE_TRAINING_EXPLAINED.md for full details.
    
    Multi-part form data:
        - voice_sample: Voice sample file (WAV/MP3, 5-10s each)
        - sample_text: Optional text that was spoken (for reference)
    
    Returns:
        {
            "success": true,
            "message": "Voice training successful! 2 samples enrolled",
            "samples_enrolled": 2,
            "samples_count": 2
        }
    
    Purpose:
    When you participate in group conversations, the system:
    1. Converts audio to text (STT)
    2. Identifies different speakers
    3. Matches speakers to enrolled voice samples
    4. Labels speakers by name instead of "Speaker 1, 2, 3..."
    
    Example Result:
    {
        "participant": "John",              # Identified by voice
        "originalText": "Let's start",
        "translatedText": "Let's start",
        "timestamp": "00:00"
    }
    
    What voice training does NOT do:
    - Does NOT teach AI what you're talking about
    - Does NOT improve AI response quality
    - Does NOT enable voice cloning
    - Does NOT act as login authentication
    
    Voice samples are stored in local database (SQLite) for speaker identification only.
    For more information, see: docs/VOICE_TRAINING_EXPLAINED.md
    """
    ctx = current_user_context()
    user_id = ctx.get('user_id')
    
    if not user_id:
        return jsonify({"success": False, "error": "Not authenticated"}), 401
    
    try:
        # Get voice sample file
        if 'voice_sample' not in request.files:
            return jsonify({"success": False, "error": "No voice sample provided"}), 400
        
        voice_file = request.files['voice_sample']
        if voice_file.filename == '':
            return jsonify({"success": False, "error": "No voice file selected"}), 400
        
        sample_text = request.form.get('sample_text', 'Voice training sample')
        
        # Read audio file
        audio_data = voice_file.read()
        if not audio_data:
            return jsonify({"success": False, "error": "Empty audio file"}), 400
        
        # Calculate audio duration
        import wave
        import io
        try:
            wav_file = wave.open(io.BytesIO(audio_data), 'rb')
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate) if rate > 0 else 0
            wav_file.close()
        except:
            duration = 0  # Estimate if we can't read
        
        # Extract voice characteristics (pitch, formants, etc.)
        voice_encoding = extract_voice_characteristics(audio_data)
        
        # Save to database
        from ..models import VoiceTraining
        from ..extensions import db
        
        training_sample = VoiceTraining(
            user_id=user_id,
            voice_sample=audio_data,
            sample_text=sample_text,
            sample_duration=duration,
            voice_encoding=json.dumps(voice_encoding) if voice_encoding else None
        )
        
        db.session.add(training_sample)
        db.session.commit()
        
        # Get total number of training samples for this user
        samples_count = VoiceTraining.query.filter_by(user_id=user_id).count()
        
        logger.info(f"Saved voice training sample for user {user_id}. Total samples: {samples_count}")
        
        return jsonify({
            "success": True,
            "samples_count": samples_count,
            "message": f"Voice sample saved successfully! You now have {samples_count} training sample(s)."
        }), 200
        
    except Exception as e:
        logger.error(f"Voice training error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


def extract_voice_characteristics(audio_data):
    """
    Extract voice characteristics from audio for speaker identification.
    
    This is a simplified version - in production, use libraries like:
    - librosa for audio feature extraction
    - pyannote for speaker verification
    
    Returns dict with voice characteristics.
    """
    try:
        import wave
        import io
        import struct
        
        wav_file = wave.open(io.BytesIO(audio_data), 'rb')
        n_channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        framerate = wav_file.getframerate()
        n_frames = wav_file.getnframes()
        
        # Read audio frames
        audio_frames = wav_file.readframes(n_frames)
        wav_file.close()
        
        # Simple pitch detection: find dominant frequency
        # This is a basic approach; production systems use more sophisticated methods
        samples = struct.unpack(f'<{len(audio_frames)//sample_width}h', audio_frames)
        
        # Calculate basic audio statistics
        max_amplitude = max(abs(s) for s in samples) if samples else 0
        rms = (sum(s**2 for s in samples) / len(samples)) ** 0.5 if samples else 0
        
        return {
            "channels": n_channels,
            "sample_rate": framerate,
            "max_amplitude": float(max_amplitude),
            "rms_energy": float(rms),
            "duration_frames": n_frames,
        }
    except Exception as e:
        logger.warning(f"Could not extract voice characteristics: {e}")
        return {}


