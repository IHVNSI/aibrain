"""Additional email endpoints: auto-reply, drafts, and send"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Blueprint, request, jsonify
from datetime import datetime
import os
import json

from ..extensions import db
from ..auth import require_auth
from ..models import DraftEmail, AutoReplySettings, StoredEmail, SentEmail
from ..email_service import EmailConfig
from ..llm.factory import build_llm

logger = logging.getLogger(__name__)

# Create blueprint
extra_email_bp = Blueprint('extra_email', __name__, url_prefix='/api/email')


# ============================================================================
# MULTI-PROMPT TASK DECOMPOSITION
# ============================================================================

def decompose_complex_task(llm, original_prompt: str, max_iterations: int = 3) -> dict:
    """
    Break down a complex task into subtasks and process iteratively.
    
    Args:
        llm: Language model instance
        original_prompt: The original complex task/query
        max_iterations: Max number of decomposition attempts
    
    Returns:
        dict with keys:
        - decomposed: bool (True if task was decomposed)
        - subtasks: list of subtask strings
        - responses: dict mapping subtask to response
        - final_answer: merged final response
        - iteration_count: number of iterations performed
    """
    result = {
        "decomposed": False,
        "subtasks": [],
        "responses": {},
        "final_answer": "",
        "iteration_count": 0
    }
    
    try:
        # Step 1: Try to decompose the task
        decomposition_prompt = f"""You are a task decomposition expert. Analyze this query and determine if it's complex and can be broken down into simpler subtasks.

Query: {original_prompt}

Respond with a JSON object:
{{
  "is_complex": boolean,
  "reason": "why or why not complex",
  "subtasks": ["subtask1", "subtask2", ...] or []
}}

Only return valid JSON, no other text."""
        
        decomposition_response = llm.chat([{"role": "user", "content": decomposition_prompt}])
        
        # Parse the decomposition response
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_str = decomposition_response
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]
            
            decomposed_data = json.loads(json_str.strip())
            
            if decomposed_data.get("is_complex") and decomposed_data.get("subtasks"):
                result["decomposed"] = True
                result["subtasks"] = decomposed_data["subtasks"]
                logger.info(f"✓ Task decomposed into {len(result['subtasks'])} subtasks")
                
                # Step 2: Process each subtask iteratively
                responses = {}
                previous_context = ""
                
                for idx, subtask in enumerate(result["subtasks"], 1):
                    logger.info(f"Processing subtask {idx}/{len(result['subtasks'])}: {subtask[:50]}...")
                    
                    # Build context including previous responses
                    subtask_prompt = f"""{subtask}

{f'Context from previous steps:' + previous_context if previous_context else ''}

Provide a clear, focused response to this subtask."""
                    
                    subtask_response = llm.chat([{"role": "user", "content": subtask_prompt}])
                    responses[subtask] = subtask_response
                    result["responses"][subtask] = subtask_response
                    
                    # Accumulate context for next iteration
                    previous_context += f"\n- {subtask}: {subtask_response[:100]}..."
                    result["iteration_count"] = idx
                
                # Step 3: Synthesize final answer from subtask responses
                synthesis_prompt = f"""Original Query: {original_prompt}

Subtasks and their responses:
"""
                for subtask, response in responses.items():
                    synthesis_prompt += f"\nSubtask: {subtask}\nResponse: {response[:200]}\n---"
                
                synthesis_prompt += "\n\nMerge all these responses into a comprehensive, coherent final answer to the original query. Ensure logical flow and eliminate redundancy."
                
                final_answer = llm.chat([{"role": "user", "content": synthesis_prompt}])
                result["final_answer"] = final_answer
                logger.info(f"✓ Synthesized final answer from {len(responses)} subtask responses")
        
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            logger.warning(f"Could not parse decomposition response: {e}. Treating as non-complex task.")
            result["decomposed"] = False
    
    except Exception as e:
        logger.warning(f"Error during task decomposition: {e}. Proceeding with original prompt.")
        result["decomposed"] = False
    
    return result


def convert_sql_dialect(sql: str, from_dialect: str = "sqlite", to_dialect: str = "mysql") -> str:
    """
    Convert SQL from one database dialect to another.
    Commonly handles SQLite → MySQL conversions.
    
    Args:
        sql: Original SQL statement
        from_dialect: Source dialect (default: sqlite)
        to_dialect: Target dialect (default: mysql)
    
    Returns:
        Converted SQL statement
    """
    if from_dialect.lower() == "sqlite" and to_dialect.lower() == "mysql":
        # SQLite to MySQL conversions
        import re
        
        # First convert datetime functions before STRFTIME conversions
        # datetime('now') → NOW()
        sql = re.sub(r"datetime\s*\(\s*'now'\s*\)", r"NOW()", sql, flags=re.IGNORECASE)
        
        # date('now') → CURDATE()
        sql = re.sub(r"date\s*\(\s*'now'\s*\)", r"CURDATE()", sql, flags=re.IGNORECASE)
        
        # Then convert STRFTIME functions
        # STRFTIME('%Y', 'now') → YEAR(NOW())
        sql = re.sub(r"STRFTIME\s*\(\s*'%Y'\s*,\s*'now'\s*\)", r"YEAR(NOW())", sql, flags=re.IGNORECASE)
        
        # STRFTIME('%m', 'now') → MONTH(NOW())
        sql = re.sub(r"STRFTIME\s*\(\s*'%m'\s*,\s*'now'\s*\)", r"MONTH(NOW())", sql, flags=re.IGNORECASE)
        
        # STRFTIME('%d', 'now') → DAY(NOW())
        sql = re.sub(r"STRFTIME\s*\(\s*'%d'\s*,\s*'now'\s*\)", r"DAY(NOW())", sql, flags=re.IGNORECASE)
        
        # STRFTIME('%Y-%m-%d', 'now') → DATE(NOW())
        sql = re.sub(r"STRFTIME\s*\(\s*'%Y-%m-%d'\s*,\s*'now'\s*\)", r"DATE(NOW())", sql, flags=re.IGNORECASE)
        
        # STRFTIME('%Y', column) → YEAR(column)
        sql = re.sub(r"STRFTIME\s*\(\s*'%Y'\s*,\s*([^)'\s][^)]*?)\)", r"YEAR(\1)", sql, flags=re.IGNORECASE)
        
        # STRFTIME('%m', column) → MONTH(column)
        sql = re.sub(r"STRFTIME\s*\(\s*'%m'\s*,\s*([^)'\s][^)]*?)\)", r"MONTH(\1)", sql, flags=re.IGNORECASE)
        
        # STRFTIME('%d', column) → DAY(column)
        sql = re.sub(r"STRFTIME\s*\(\s*'%d'\s*,\s*([^)'\s][^)]*?)\)", r"DAY(\1)", sql, flags=re.IGNORECASE)
        
        # STRFTIME('%Y-%m-%d', column) → DATE(column)
        sql = re.sub(r"STRFTIME\s*\(\s*'%Y-%m-%d'\s*,\s*([^)'\s][^)]*?)\)", r"DATE(\1)", sql, flags=re.IGNORECASE)
        
        logger.info(f"✓ Converted SQL from SQLite to MySQL dialect")
    
    return sql


def handle_sql_execution_error(svc, llm, original_sql: str, error: Exception, email_content: str, attempt: int = 1, max_attempts: int = 2) -> tuple[bool, str]:
    """
    Handle SQL execution errors with intelligent retry and correction.
    
    Args:
        svc: Vanna service instance
        llm: Language model instance
        original_sql: The SQL that failed to execute
        error: The exception that was raised
        email_content: Original email content for context
        attempt: Current attempt number
        max_attempts: Maximum retry attempts
    
    Returns:
        Tuple of (success_flag, corrected_sql_or_empty_string)
    """
    error_msg = str(error)
    logger.warning(f"📋 SQL Execution Error (Attempt {attempt}/{max_attempts}): {error_msg[:100]}")
    
    # Check if this is a database dialect error (function doesn't exist)
    is_dialect_error = any(keyword in error_msg.lower() for keyword in [
        "no such function", "function does not exist", "unknown function",
        "1305", "1064"  # MySQL error codes for unknown function/syntax error
    ])
    
    if not is_dialect_error or attempt >= max_attempts:
        logger.warning(f"⚠️  Cannot auto-correct: dialect_error={is_dialect_error}, attempt={attempt}/{max_attempts}")
        return False, ""
    
    try:
        # Try dialect conversion first (most common: SQLite → MySQL)
        logger.info(f"🔧 Attempting dialect conversion (SQLite → MySQL)...")
        corrected_sql = convert_sql_dialect(original_sql, from_dialect="sqlite", to_dialect="mysql")
        
        if corrected_sql != original_sql:
            logger.info(f"✅ SQL converted: {corrected_sql[:80]}...")
            return True, corrected_sql
        
        # If conversion didn't help, try Vanna's error correction
        logger.info(f"🔧 Attempting Vanna error correction...")
        history = []
        corrected_sql = svc.correct_sql(
            question=email_content,
            bad_sql=original_sql,
            error_message=error_msg,
            history=history
        )
        
        if corrected_sql and corrected_sql.strip().upper().startswith('SELECT'):
            logger.info(f"✅ SQL corrected via Vanna: {corrected_sql[:80]}...")
            return True, corrected_sql
        else:
            logger.warning(f"⚠️  Vanna correction did not yield valid SELECT statement")
            return False, ""
    
    except Exception as correction_error:
        logger.warning(f"⚠️  Error correction attempt failed: {correction_error}")
        return False, ""


def retry_sql_generation_with_correction(svc, llm, email_content: str, previous_error: str = "", attempt: int = 1, max_attempts: int = 2) -> tuple[str, bool]:
    """
    Retry SQL generation with error correction if initial attempt fails.
    
    Args:
        svc: Vanna service instance
        llm: Language model instance
        email_content: Original email content
        previous_error: Error from previous attempt
        attempt: Current attempt number
        max_attempts: Maximum retry attempts
    
    Returns:
        Tuple of (generated_sql, success_flag)
    """
    if attempt > max_attempts:
        logger.warning(f"Max SQL generation attempts ({max_attempts}) reached")
        return "", False
    
    try:
        if previous_error:
            # Use error correction if we have a previous error
            history = []
            corrected_sql = svc.correct_sql(email_content, "", previous_error, history)
            if corrected_sql and corrected_sql.strip().upper().startswith('SELECT'):
                logger.info(f"✓ SQL corrected on attempt {attempt}: {corrected_sql[:80]}...")
                return corrected_sql, True
        else:
            # First attempt - regular SQL generation
            history = []
            generated_sql = svc.generate_sql_multiturn(email_content, history)
            if generated_sql and generated_sql.strip().upper().startswith('SELECT'):
                logger.info(f"✓ SQL generated on attempt {attempt}: {generated_sql[:80]}...")
                return generated_sql, True
        
        logger.warning(f"SQL generation attempt {attempt} did not yield valid SELECT statement")
        return "", False
    
    except Exception as e:
        logger.warning(f"Error during SQL generation attempt {attempt}: {e}")
        return "", False


# ============================================================================
# SENDER EMAIL VERIFICATION & CONTACT LOOKUP
# ============================================================================

@extra_email_bp.route('/sender-info', methods=['POST'])
@require_auth
def get_sender_info():
    """
    Look up sender contact information by email.
    
    Searches the source database (contacts table) and personnel table
    to find matching email and return customer/employee info.
    
    Request body:
        {
            "email": "customer@example.com"
        }
    
    Returns:
        {
            "success": true,
            "contact": {
                "type": "customer|employee|unknown",
                "name": "John Smith",
                "email": "john@example.com",
                "organization": "Smith Corp",
                "phone": "555-1234",
                "table": "contacts|personnel"
            }
        }
    """
    try:
        data = request.json or {}
        email = (data.get('email') or '').strip().lower()
        
        if not email or '@' not in email:
            return jsonify({
                "success": True,
                "contact": None,
                "reason": "Invalid email address"
            }), 200
        
        # Try to query the source database for matching contact
        try:
            from ..vanna_service import get_vanna_service
            svc = get_vanna_service()
            
            if not svc.ready or not svc._connected_db:
                logger.warning("Vanna service not ready for contact lookup")
                return jsonify({
                    "success": True,
                    "contact": None,
                    "reason": "Database not configured"
                }), 200
            
            # Try to find in contacts table
            # Query pattern: SELECT * FROM contacts WHERE email = ?
            try:
                from sqlalchemy import create_engine, text
                import pandas as pd
                
                engine = create_engine(svc._connected_db, connect_args={"timeout": 10})
                
                # Try common table/column name patterns
                contact = None
                tables_to_try = [
                    ('contacts', 'email', ['name', 'organization', 'phone', 'company']),
                    ('customers', 'email', ['name', 'organization', 'phone']),
                    ('personnel', 'email', ['name', 'department', 'phone']),
                    ('employees', 'email', ['name', 'department', 'phone']),
                    ('staff', 'email', ['name', 'department', 'phone']),
                    ('users', 'email', ['name', 'organization']),
                ]
                
                for table_name, email_col, name_cols in tables_to_try:
                    try:
                        # Check if table exists
                        query = f"SELECT * FROM {table_name} WHERE LOWER({email_col}) = LOWER(:email) LIMIT 1"
                        df = pd.read_sql_query(
                            text(query),
                            engine,
                            params={"email": email}
                        )
                        
                        if not df.empty and len(df) > 0:
                            row = df.iloc[0].to_dict()
                            
                            # Extract contact info
                            contact_info = {
                                "type": "customer" if table_name in ['contacts', 'customers'] else "employee",
                                "email": email,
                                "table": table_name,
                                "raw_data": {k: str(v) if pd.notna(v) else None for k, v in row.items()}
                            }
                            
                            # Try to find name column
                            for col in name_cols + ['name', 'full_name', 'contact_name']:
                                if col.lower() in [c.lower() for c in df.columns]:
                                    contact_info["name"] = str(row.get(col, ''))
                                    break
                            
                            # Try to find organization column
                            for col in ['organization', 'company', 'company_name', 'org']:
                                if col.lower() in [c.lower() for c in df.columns]:
                                    contact_info["organization"] = str(row.get(col, ''))
                                    break
                            
                            # Try to find phone column
                            for col in ['phone', 'phone_number', 'telephone', 'mobile']:
                                if col.lower() in [c.lower() for c in df.columns]:
                                    contact_info["phone"] = str(row.get(col, ''))
                                    break
                            
                            logger.info(f"✓ Found contact for {email} in {table_name} table")
                            contact = contact_info
                            break
                    except Exception as e:
                        # Table might not exist, try next one
                        logger.debug(f"Table {table_name} query failed: {e}")
                        continue
                
                engine.dispose()
                
                return jsonify({
                    "success": True,
                    "contact": contact
                }), 200
            
            except Exception as e:
                logger.warning(f"Error querying source database for contact: {e}")
                return jsonify({
                    "success": True,
                    "contact": None,
                    "reason": str(e)
                }), 200
        
        except Exception as e:
            logger.warning(f"Error in sender info lookup: {e}")
            return jsonify({
                "success": True,
                "contact": None,
                "reason": str(e)
            }), 200
    
    except Exception as e:
        logger.error(f"Unexpected error in sender-info endpoint: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================================
# EMAIL FORMATTING UTILITIES
# ============================================================================

def convert_text_to_html_email(plain_text: str, sender_email: str = None) -> tuple[str, str]:
    """
    Convert plain text email response to properly formatted HTML email with:
    - Proper paragraph tags
    - Bold text formatting (convert ** to <strong>)
    - Email salutation (greeting and closing)
    - Professional structure
    
    Args:
        plain_text: Plain text email body from LLM
        sender_email: Sender's email address (for extracting name)
    
    Returns:
        Tuple of (plain_text_formatted, html_text_formatted)
    """
    try:
        import re
        
        # Extract sender's first name from email if available
        sender_name = "Valued Customer"
        if sender_email and '@' in sender_email:
            name_part = sender_email.split('@')[0]
            # Capitalize each word and handle common patterns
            sender_name = name_part.replace('.', ' ').replace('_', ' ').title()
        
        # Split text into paragraphs (double newlines or single newlines)
        paragraphs = []
        current_para = []
        
        for line in plain_text.strip().split('\n'):
            line = line.strip()
            if line:
                current_para.append(line)
            elif current_para:
                # Empty line indicates paragraph break
                paragraphs.append(' '.join(current_para))
                current_para = []
        
        if current_para:
            paragraphs.append(' '.join(current_para))
        
        # Filter out empty paragraphs
        paragraphs = [p for p in paragraphs if p.strip()]
        
        # Convert markdown bold (**text**) to HTML strong tags
        def replace_bold(text):
            return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        
        # Build HTML content
        html_parts = []
        
        # Add opening salutation
        html_parts.append(f'<p>Dear {sender_name},</p>')
        html_parts.append('<p></p>')  # Blank line for spacing
        
        # Add body paragraphs with bold formatting
        for para in paragraphs:
            # Skip if this is a typical closing (we'll add our own)
            if para.lower().startswith(('best regards', 'sincerely', 'regards', 
                                       'thank you', 'warm regards', 'yours truly')):
                continue
            
            # Apply bold formatting
            para_with_bold = replace_bold(para)
            html_parts.append(f'<p>{para_with_bold}</p>')
        
        # Add closing salutation
        html_parts.append('<p></p>')  # Blank line for spacing
        html_parts.append('<p>Best regards,<br/>Support Team</p>')
        
        # Join all parts
        html_body = '\n'.join(html_parts)
        
        # Create plain text version (removing HTML tags but keeping structure)
        plain_text_formatted = f"""Dear {sender_name},

{chr(10).join(paragraphs)}

Best regards,
Support Team"""
        
        logger.info(f"✓ Converted text to HTML email format ({len(html_parts)} parts)")
        
        return plain_text_formatted, html_body
    
    except Exception as e:
        logger.warning(f"Error converting text to HTML email: {e}")
        # Return original text as fallback
        return plain_text, plain_text


# ============================================================================
# AUTO-REPLY ENDPOINTS
# ============================================================================

@extra_email_bp.route('/auto-reply/settings', methods=['GET'])
@require_auth
def get_auto_reply_settings():
    """Get auto-reply configuration."""
    try:
        settings = AutoReplySettings.query.first()
        if not settings:
            # Create default settings if none exist
            settings = AutoReplySettings(
                enabled=False,
                mode='review',
                ai_instructions='Be professional and concise in your response.',
                use_database=True,
                enabled_folders='INBOX'
            )
            db.session.add(settings)
            db.session.commit()
        
        return jsonify({
            "success": True,
            "settings": settings.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting auto-reply settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@extra_email_bp.route('/auto-reply/settings', methods=['POST'])
@require_auth
def update_auto_reply_settings():
    """Update auto-reply configuration."""
    try:
        data = request.json or {}
        
        settings = AutoReplySettings.query.first()
        if not settings:
            settings = AutoReplySettings()
        
        # Update fields
        if 'enabled' in data:
            settings.enabled = data['enabled']
        if 'mode' in data:
            settings.mode = data['mode']  # 'auto' or 'review'
        if 'ai_instructions' in data:
            settings.ai_instructions = data['ai_instructions']
        if 'use_database' in data:
            settings.use_database = data['use_database']
        if 'database_context' in data:
            import json
            settings.database_context = json.dumps(data['database_context'])
        if 'reply_template' in data:
            settings.reply_template = data['reply_template']
        if 'enabled_folders' in data:
            if isinstance(data['enabled_folders'], list):
                settings.enabled_folders = ','.join(data['enabled_folders'])
            else:
                settings.enabled_folders = data['enabled_folders']
        
        db.session.add(settings)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Auto-reply settings updated",
            "settings": settings.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Error updating auto-reply settings: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@extra_email_bp.route('/auto-reply/generate', methods=['POST'])
@require_auth
def generate_auto_reply():
    """
    Generate an intelligent auto-reply for a specific email using AI + Vanna.ai.
    
    Features:
    1. Analyzes email content to detect data queries
    2. Uses Vanna to generate SQL if needed
    3. Fetches data from database with authorization checks
    4. Includes fetched data in LLM response context
    5. Generates professional reply with actual data
    
    Request body:
    {
        "email_id": 123,  // ID of StoredEmail to reply to
        "custom_prompt": "Please mention the project status"  // Optional context
    }
    """
    try:
        from ..auth import current_user_context
        from ..vanna_service import get_vanna_service
        from ..responder import compose_answer
        
        data = request.json or {}
        email_id = data.get('email_id')
        custom_prompt = data.get('custom_prompt', '')
        
        if not email_id:
            return jsonify({"success": False, "error": "email_id required"}), 400
        
        # Get the email to reply to
        email = StoredEmail.query.get(email_id)
        if not email:
            return jsonify({"success": False, "error": "Email not found"}), 404
        
        # Check sender authorization - only authorized senders can trigger database queries
        from ..models import AuthorizedContact
        sender_authorized = AuthorizedContact.query.filter_by(
            contact=email.from_address,
            contact_type='email',
            is_active=True
        ).first()
        
        logger.info(f"📧 Email from {email.from_address}: authorized={bool(sender_authorized)}")
        
        # ============================================================
        # CHECK PER-CONTACT AUTO-REPLY SETTINGS
        # ============================================================
        auto_reply_mode = 'draft'  # Default to draft mode
        per_contact_instructions = None
        
        if sender_authorized:
            if not sender_authorized.auto_reply_enabled:
                logger.info(f"⛔ Auto-reply disabled for sender {email.from_address}")
                return jsonify({"success": False, "error": f"Auto-reply not enabled for {email.from_address}"}), 400
            
            # Use per-contact settings
            auto_reply_mode = sender_authorized.auto_reply_mode  # 'draft' or 'send'
            per_contact_instructions = sender_authorized.auto_reply_ai_instructions
            logger.info(f"✓ Using per-contact auto-reply settings: mode='{auto_reply_mode}'")
        
        # Get global auto-reply settings as fallback
        settings = AutoReplySettings.query.first()
        if not settings or not settings.enabled:
            logger.info("⚠️  Global auto-reply not enabled, but per-contact auto-reply may still apply")
            # For per-contact auto-reply, we can proceed even if global is disabled
            if not sender_authorized:
                return jsonify({"success": False, "error": "Auto-reply not enabled"}), 400
            settings = AutoReplySettings()  # Create temporary settings object with defaults
        
        
        # Get LLM and Vanna service
        llm = build_llm()
        if not llm:
            return jsonify({"success": False, "error": "LLM not configured"}), 500
        
        svc = get_vanna_service()
        if not svc.ready:
            logger.warning("Vanna service not ready for email auto-reply")
            svc = None
        
        # Get full system context
        from app.models import AIContext, TrainingItem
        
        ai_context = AIContext.get_active()
        system_instructions = ai_context.system_instructions if ai_context else "You are a professional and helpful assistant."
        
        # Get training items for context
        training_items = TrainingItem.query.limit(10).all()
        training_context = ""
        if training_items:
            training_context = "\n\nTraining Context:"
            for item in training_items:
                if item.metadata and 'description' in item.metadata:
                    training_context += f"\n- {item.metadata['description']}"
        
        # Attempt to fetch database data using Vanna if available
        # IMPORTANT: Only proceed if sender is authorized
        database_data = ""
        fetched_rows = []
        fetched_columns = []
        generated_sql = ""
        used_multi_prompt = False
        
        # Guard: Only query database if sender is authorized
        if settings.use_database and not sender_authorized:
            logger.warning(f"⛔ Database query blocked: sender '{email.from_address}' not authorized")
            # Continue with info-only reply (no database data)
        elif svc and settings.use_database and sender_authorized:
            logger.info("🔍 Attempting to fetch database data for email reply...")
            try:
                email_content = email.body or email.html_body or ""
                
                # Step 1: Try standard SQL generation
                generated_sql, sql_success = retry_sql_generation_with_correction(svc, llm, email_content, attempt=1)
                
                # Step 2: If standard generation failed, try multi-prompt decomposition
                if not sql_success:
                    logger.info("📋 Standard SQL generation failed. Attempting multi-prompt task decomposition...")
                    decomposition_result = decompose_complex_task(llm, email_content, max_iterations=2)
                    
                    if decomposition_result["decomposed"] and decomposition_result["final_answer"]:
                        logger.info(f"✓ Multi-prompt decomposition successful ({decomposition_result['iteration_count']} iterations)")
                        database_data = f"\n\n[Task Decomposed and Analyzed]\nResponse synthesized from {decomposition_result['iteration_count']} analysis steps:\n{decomposition_result['final_answer']}"
                        used_multi_prompt = True
                    else:
                        logger.warning("Multi-prompt decomposition did not generate database query")
                
                # Step 3: Execute SQL if we have one
                if generated_sql and generated_sql.strip():
                    logger.info(f"📊 Generated SQL for email: {generated_sql}")
                    
                    # Execute the SQL safely
                    from .. import sql_guard
                    
                    # Validate SQL - use relaxed validation for authorized auto-reply senders
                    # Authorized senders can perform more operations than chat-only users
                    if sender_authorized:
                        # For authorized senders, just check for truly dangerous operations
                        dangerous_keywords = ['DROP', 'TRUNCATE', 'GRANT', 'REVOKE', 'PRAGMA', 'EXEC']
                        sql_upper = generated_sql.strip().upper()
                        is_dangerous = any(keyword in sql_upper for keyword in dangerous_keywords)
                        
                        if is_dangerous:
                            logger.warning(f"⛔ SQL blocked for security: Contains dangerous operations")
                            safe = False
                            reason = "SQL contains dangerous operations (DROP, TRUNCATE, GRANT, REVOKE, etc.)"
                        else:
                            # Authorized sender can do SELECT, INSERT, UPDATE, DELETE
                            safe = True
                            reason = "Authorized sender - elevated permissions for auto-reply operations"
                            logger.info(f"✓ SQL authorized for auto-reply (sender: {email.from_address})")
                    else:
                        # For non-authorized senders, use strict chat-only validation (read-only)
                        safe, reason = sql_guard.validate(generated_sql, is_admin=False)
                    
                    if safe:
                        # Additional validation: Check for column existence before execution
                        col_valid, col_reason = svc.validate_sql_columns(generated_sql)
                        if not col_valid:
                            logger.warning(f"⚠️  SQL columns validation failed: {col_reason}")
                            # Log but don't block - column errors will be caught at execution time
                        
                        # Execute query
                        sql_to_execute = generated_sql
                        sql_attempt = 1
                        max_sql_attempts = 2
                        
                        while sql_attempt <= max_sql_attempts:
                            try:
                                # Execute SQL via Vanna service and handle results
                                df = svc.run_sql(sql_to_execute)
                                if df is not None and len(df) > 0:
                                    columns = list(df.columns)
                                    rows = df.head(500).to_dict(orient="records")
                                    # Convert any non-JSON-serializable objects (Timestamp, datetime, etc.) to strings
                                    from app.api.chat import _convert_rows_to_serializable
                                    rows = _convert_rows_to_serializable(rows)
                                    row_count = len(df)
                                    run_error = None
                                else:
                                    rows, columns, row_count, run_error = [], [], 0, None
                                
                                if not run_error and rows:
                                    fetched_rows = rows[:20]  # Limit to 20 rows for email
                                    fetched_columns = columns
                                    
                                    # Format data naturally for incorporation into email response
                                    database_data = "\n\nRELEVANT INFORMATION FROM OUR RECORDS:\n"
                                    database_data += "-" * 50 + "\n"
                                    
                                    # Format each row as human-readable information
                                    for i, row in enumerate(fetched_rows[:10], 1):
                                        for col, value in row.items():
                                            # Format column name nicely
                                            nice_col = col.replace('_', ' ').title()
                                            database_data += f"{nice_col}: {value}\n"
                                        if i < len(fetched_rows[:10]):
                                            database_data += "-" * 50 + "\n"
                                    
                                    logger.info(f"✓ Fetched {row_count} rows from database for email reply")
                                
                                # Successfully executed, break the retry loop
                                break
                                
                            except Exception as e:
                                # Attempt error correction if this is a dialect error
                                success, corrected_sql = handle_sql_execution_error(
                                    svc, llm, sql_to_execute, e, 
                                    email_content, sql_attempt, max_sql_attempts
                                )
                                
                                if success and corrected_sql:
                                    # Retry with corrected SQL
                                    logger.info(f"🔄 Retrying SQL execution with corrected statement (attempt {sql_attempt + 1})")
                                    sql_to_execute = corrected_sql
                                    sql_attempt += 1
                                else:
                                    # Could not correct, give up
                                    logger.warning(f"❌ SQL execution failed after {sql_attempt} attempt(s): {e}")
                                    database_data = f"\n\nNote: Could not fetch database data - {str(e)[:100]}"
                                    break
                    else:
                        logger.warning(f"Generated SQL blocked for safety: {reason}")
            except Exception as e:
                logger.warning(f"Could not generate SQL from email content: {e}")
        elif not sender_authorized and settings.use_database:
            logger.info(f"⛔ Sender {email.from_address} not authorized for database queries")
        
        # Build comprehensive email prompt
        email_prompt = f"""You are a professional business support representative responding to a customer email.

INCOMING EMAIL:
From: {email.from_address}
Subject: {email.subject}
Received: {email.received_date.isoformat() if email.received_date else 'Today'}

Message:
{email.body or email.html_body or '(no content)'}

{f'RELEVANT DATA TO REFERENCE:{database_data}' if database_data else ''}

{f'ADDITIONAL CONTEXT: {custom_prompt}' if custom_prompt else ''}

RESPONSE GUIDELINES:
1. Write a professional, helpful response from a human team member
2. Address the customer's concerns directly and thoroughly  
3. Use the data naturally in your response (don't mention where it came from)
4. Keep the tone warm, professional, and courteous
5. If data is available, incorporate it naturally into the conversation
6. Format the response with:
   - A warm greeting using the customer's name or formal salutation
   - Direct address of their questions/concerns
   - Relevant details or information
   - A professional closing signature
7. Never indicate this is automated, AI-generated, or system-generated
8. Sound like a knowledgeable human professional
9. Be concise but complete in your response

IMPORTANT:
- Output ONLY the email body response
- No meta-commentary, explanations, or system messages
- Include greeting and closing within the response
- Make it personal and human

{f'TONE GUIDELINES: {per_contact_instructions or settings.ai_instructions}' if (per_contact_instructions or settings.ai_instructions) else ''}

Now write the professional, human response email:"""
        
        # Generate response using LLM - with fallback chain to ensure we never fail
        response_text = None
        response_method = ""
        
        try:
            if used_multi_prompt and database_data:
                # Multi-prompt decomposition already included in database_data
                # Just use LLM chat with the enhanced context
                messages = [{"role": "user", "content": email_prompt}]
                response_text = llm.chat(messages)
                response_method = "multi_prompt_synthesis"
            elif fetched_rows and fetched_columns:
                # Use compose_answer for data-driven response
                try:
                    response_text = compose_answer(
                        llm,
                        email.body or email.html_body,
                        generated_sql,
                        fetched_columns,
                        fetched_rows,
                        len(fetched_rows),
                        run_error=None
                    )
                    response_method = "compose_answer_with_data"
                    if not response_text:
                        raise ValueError("compose_answer returned None")
                except Exception as e:
                    logger.warning(f"compose_answer failed: {e}. Falling back to standard LLM chat.")
                    messages = [{"role": "user", "content": email_prompt}]
                    response_text = llm.chat(messages)
                    response_method = "fallback_llm_chat"
            else:
                # Standard LLM response for non-data queries
                messages = [{"role": "user", "content": email_prompt}]
                response_text = llm.chat(messages)
                response_method = "text_only_response"
            
            # Apply reply template if configured
            if response_text and settings.reply_template:
                try:
                    # Template variables: {response}, {sender}, {subject}, {data}
                    sender_name = email.from_address.split('@')[0].title() if email.from_address else "valued customer"
                    template_context = {
                        "response": response_text.strip(),
                        "sender": sender_name,
                        "subject": email.subject or "Your Inquiry",
                        "data": database_data.strip() if database_data else "",
                        "sender_email": email.from_address,
                        "date": email.received_date.isoformat() if email.received_date else "today"
                    }
                    # Use template with context
                    response_text = settings.reply_template.format(**template_context)
                    response_method = f"{response_method}_with_template"
                    logger.info(f"✓ Applied reply template from Auto-Reply Configuration")
                except Exception as e:
                    logger.warning(f"⚠️  Could not apply reply template: {e}. Using generated response.")
        
        except Exception as e:
            logger.error(f"Error generating response: {e}. Creating minimal draft.")
            response_text = None
        
        # BULLETPROOF: If response generation fails, create a fallback response
        if not response_text:
            logger.warning("⚠️  Response generation failed. Creating minimal fallback draft.")
            # Extract sender name if possible
            sender_name = email.from_address.split('@')[0].title() if email.from_address else "Valued Customer"
            response_text = f"""Dear {sender_name},

Thank you for reaching out to us regarding "{email.subject}".

We appreciate you taking the time to contact us. Your message is important to us, and we are committed to providing you with the assistance you need.

Our team is actively reviewing your inquiry and will get back to you as soon as possible with a comprehensive response.

We look forward to helping you.

Best regards,
Support Team"""
            response_method = "fallback_minimal"
        
        # Prepare context for draft (always succeeds, even if response generation partially failed)
        full_context = {
            "system_instructions": system_instructions,
            "training_context": training_context,
            "database_data_fetched": bool(fetched_rows),
            "generated_sql": generated_sql if generated_sql else None,
            "rows_fetched": len(fetched_rows),
            "sender_authorized": bool(sender_authorized),
            "multi_prompt_used": used_multi_prompt,
            "response_method": response_method,
            "auto_reply_mode": auto_reply_mode
        }
        
        # ============================================================
        # CREATE DRAFT & HANDLE AUTO-SEND
        # ============================================================
        draft = None
        sent_email = None
        draft_status = 'pending_review'  # Default for draft mode
        
        # Determine draft status and whether to auto-send
        if auto_reply_mode == 'send':
            draft_status = 'pending_review'  # Create draft first, then send
        
        # Convert response text to HTML email format
        body_text = response_text if response_text else "(Auto-reply generation encountered issues. Please review.)"
        plain_text_body, html_body = convert_text_to_html_email(body_text, email.from_address)
        
        try:
            # Create draft email with AI context
            draft = DraftEmail(
                to_address=email.from_address,
                subject=f"Re: {email.subject}",
                body=plain_text_body,
                html_body=html_body,
                status=draft_status,
                in_reply_to=email_id,
                auto_generated=True,
                ai_prompt=email_prompt,
                ai_context=json.dumps(full_context)
            )
            db.session.add(draft)
            db.session.commit()
            
            logger.info(f"✓ Draft created for {email.from_address} (status={draft_status})")
            
            # ============================================================
            # AUTO-SEND IF MODE IS 'SEND'
            # ============================================================
            if auto_reply_mode == 'send':
                logger.info(f"📤 Auto-sending reply to {email.from_address} (no human oversight required)")
                
                try:
                    # Import email sending function
                    from ..email_service import send_email_via_service
                    
                    # Prepare email configuration
                    from ..email_service import EmailConfig
                    config = EmailConfig.get_current()
                    
                    if not config or not config.smtp_server or not config.from_address:
                        logger.error("❌ Email configuration not available for auto-send")
                        # Mark draft with error
                        draft.status = 'failed'
                        draft.error_message = "Email configuration not available for auto-send"
                        db.session.commit()
                    else:
                        # Send the email
                        try:
                            send_result = send_email_via_service(
                                recipient=email.from_address,
                                subject=f"Re: {email.subject}",
                                body=plain_text_body,
                                html_body=html_body,
                                cc_list=[],
                                bcc_list=[],
                                config=config
                            )
                            
                            if send_result.get('success'):
                                logger.info(f"✅ Email auto-sent to {email.from_address}")
                                
                                # Create SentEmail record
                                sent_email = SentEmail(
                                    to_address=email.from_address,
                                    subject=f"Re: {email.subject}",
                                    body=plain_text_body,
                                    html_body=html_body,
                                    in_reply_to=email_id,
                                    from_draft=draft.id,
                                    ai_generated=True,
                                    ai_context=json.dumps(full_context),
                                    status='sent'
                                )
                                db.session.add(sent_email)
                                
                                # Mark draft as sent
                                draft.status = 'sent'
                                draft.sent_at = datetime.utcnow()
                                
                                db.session.commit()
                                
                                logger.info(f"✓ SentEmail record created for auto-sent reply")
                            else:
                                # Send failed
                                error_msg = send_result.get('error', 'Unknown error')
                                logger.error(f"❌ Failed to auto-send email: {error_msg}")
                                draft.status = 'failed'
                                draft.error_message = f"Auto-send failed: {error_msg}"
                                db.session.commit()
                        
                        except Exception as e:
                            logger.error(f"❌ Error during auto-send: {e}", exc_info=True)
                            draft.status = 'failed'
                            draft.error_message = f"Auto-send error: {str(e)[:200]}"
                            db.session.commit()
                
                except ImportError as e:
                    logger.error(f"❌ Could not import email service: {e}")
                    draft.status = 'failed'
                    draft.error_message = "Email service not available for auto-send"
                    db.session.commit()
            else:
                # Draft mode - just save for manual review
                logger.info(f"📝 Draft saved for manual review by {email.from_address}")
        
        except Exception as e:
            logger.error(f"Error creating draft: {e}", exc_info=True)
            db.session.rollback()
            
            # ABSOLUTE FALLBACK: Try creating minimal draft without context
            try:
                fallback_body = response_text if response_text else "Thank you for your email. A response will be provided shortly."
                _, fallback_html = convert_text_to_html_email(fallback_body, email.from_address)
                
                draft = DraftEmail(
                    to_address=email.from_address,
                    subject=f"Re: {email.subject}",
                    body=fallback_body,
                    html_body=fallback_html,
                    status='pending_review',
                    in_reply_to=email_id,
                    auto_generated=True
                )
                db.session.add(draft)
                db.session.commit()
                logger.warning(f"✓ Minimal draft created as fallback (original error: {e})")
            except Exception as fallback_error:
                logger.critical(f"CRITICAL: Could not create draft even in fallback mode: {fallback_error}", exc_info=True)
                # Return error but with information about what happened
                return jsonify({
                    "success": False,
                    "error": "Could not save draft to database",
                    "context": {
                        "response_generated": bool(response_text),
                        "data_fetched": bool(fetched_rows),
                        "sender_authorized": bool(sender_authorized),
                        "original_error": str(e),
                        "fallback_error": str(fallback_error)
                    }
                }), 500
        
        # Build response message based on authorization and data fetch status
        if sent_email:
            response_message = f"✅ Reply auto-sent to {email.from_address}"
        elif sender_authorized and fetched_rows:
            response_message = f"Auto-reply generated with database data ({len(fetched_rows)} rows) and saved as draft"
        elif sender_authorized and used_multi_prompt:
            response_message = "Auto-reply generated using multi-prompt task decomposition and saved as draft"
        elif sender_authorized:
            response_message = "Auto-reply generated (no database data available for query) and saved as draft"
        else:
            response_message = "Auto-reply generated (info-only, sender not authorized for database access) and saved as draft"
        
        return jsonify({
            "success": True,
            "message": response_message,
            "auto_reply_mode": auto_reply_mode,
            "draft": draft.to_dict() if draft else {"id": None, "status": "pending_review", "subject": f"Re: {email.subject}"},
            "sent_email": sent_email.to_dict() if sent_email else None,
            "context": {
                "data_fetched": bool(fetched_rows),
                "rows_count": len(fetched_rows),
                "sender_authorized": bool(sender_authorized),
                "generated_sql": generated_sql if generated_sql else None,
                "multi_prompt_used": used_multi_prompt,
                "response_method": response_method,
                "auto_sent": bool(sent_email)
            }
        }), 201
    
    except Exception as e:
        logger.error(f"Error generating auto-reply: {e}", exc_info=True)
        db.session.rollback()
        
        # Final catchall - return minimal response
        return jsonify({
            "success": False,
            "error": f"Auto-reply generation failed: {str(e)}",
            "context": {
                "error_type": type(e).__name__
            }
        }), 500


# ============================================================================
# DRAFT & OUTBOX ENDPOINTS
# ============================================================================

@extra_email_bp.route('/drafts', methods=['GET'])
@require_auth
def get_drafts():
    """Get all draft emails (for outbox)."""
    try:
        status = request.args.get('status', 'draft')  # draft, pending_review, sent, failed
        
        query = DraftEmail.query
        if status:
            query = query.filter_by(status=status)
        
        drafts = query.order_by(DraftEmail.created_at.desc()).all()
        
        return jsonify({
            "success": True,
            "drafts": [d.to_dict() for d in drafts],
            "count": len(drafts)
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting drafts: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@extra_email_bp.route('/drafts', methods=['POST'])
@require_auth
def create_draft():
    """
    Create a new draft email.
    
    Request body:
    {
        "to_address": "recipient@example.com",
        "subject": "Email subject",
        "body": "Email body content",
        "html_body": "<p>HTML content</p>",
        "in_reply_to": 123  // Optional: if replying to StoredEmail
    }
    """
    try:
        data = request.json or {}
        
        # Validate required fields
        required = ['to_address', 'subject', 'body']
        if not all(k in data for k in required):
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {required}"
            }), 400
        
        # Create draft
        draft = DraftEmail(
            to_address=data['to_address'],
            cc_address=data.get('cc_address'),
            bcc_address=data.get('bcc_address'),
            subject=data['subject'],
            body=data['body'],
            html_body=data.get('html_body'),
            in_reply_to=data.get('in_reply_to'),
            status='draft'
        )
        db.session.add(draft)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Draft created",
            "draft": draft.to_dict()
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating draft: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@extra_email_bp.route('/drafts/<int:draft_id>', methods=['PUT'])
@require_auth
def update_draft(draft_id):
    """Update a draft email."""
    try:
        draft = DraftEmail.query.get(draft_id)
        if not draft:
            return jsonify({"success": False, "error": "Draft not found"}), 404
        
        data = request.json or {}
        
        # Update fields
        if 'to_address' in data:
            draft.to_address = data['to_address']
        if 'cc_address' in data:
            draft.cc_address = data['cc_address']
        if 'bcc_address' in data:
            draft.bcc_address = data['bcc_address']
        if 'subject' in data:
            draft.subject = data['subject']
        if 'body' in data:
            draft.body = data['body']
        if 'html_body' in data:
            draft.html_body = data['html_body']
        
        draft.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Draft updated",
            "draft": draft.to_dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Error updating draft: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@extra_email_bp.route('/drafts/<int:draft_id>', methods=['DELETE'])
@require_auth
def delete_draft(draft_id):
    """Delete a draft email."""
    try:
        draft = DraftEmail.query.get(draft_id)
        if not draft:
            return jsonify({"success": False, "error": "Draft not found"}), 404
        
        db.session.delete(draft)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Draft deleted"
        }), 200
    
    except Exception as e:
        logger.error(f"Error deleting draft: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# SEND EMAIL ENDPOINTS
# ============================================================================

def send_email_smtp(to_address, subject, body, cc_address=None, bcc_address=None):
    """Send email via SMTP with optional CC and BCC."""
    try:
        email_address = os.getenv('EMAIL_ADDRESS')
        email_password = os.getenv('EMAIL_PASSWORD')
        email_provider = os.getenv('EMAIL_PROVIDER', 'gmail').lower()
        
        # SMTP Configuration
        smtp_config = {
            'gmail': ('smtp.gmail.com', 587),
            'outlook': ('smtp-mail.outlook.com', 587),
            'yahoo': ('smtp.mail.yahoo.com', 587),
            'icloud': ('smtp.mail.icloud.com', 587),
            'custom': (os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com'), 
                      int(os.getenv('EMAIL_SMTP_PORT', '587')))
        }
        
        smtp_server, smtp_port = smtp_config.get(
            email_provider,
            ('smtp.gmail.com', 587)
        )
        
        # Determine if using SSL
        use_ssl = int(smtp_port) == 465
        
        # Create MIME message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = email_address
        msg['To'] = to_address
        
        # Add CC and BCC headers
        if cc_address:
            msg['Cc'] = cc_address
        if bcc_address:
            msg['Bcc'] = bcc_address
        
        # Attach body as HTML
        msg.attach(MIMEText(body, 'html'))
        
        # Connect and send
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, int(smtp_port))
        else:
            server = smtplib.SMTP(smtp_server, int(smtp_port))
            server.starttls()
        
        try:
            server.login(email_address, email_password)
            # Combine all recipients for sending
            recipients = [to_address]
            if cc_address:
                recipients.extend([e.strip() for e in cc_address.split(',')])
            if bcc_address:
                recipients.extend([e.strip() for e in bcc_address.split(',')])
            server.sendmail(email_address, recipients, msg.as_string())
            logger.info(f"Email sent to {to_address}")
            return True
        finally:
            server.quit()
    
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


@extra_email_bp.route('/send', methods=['POST'])
@require_auth
def send_email():
    """
    Send an email directly.
    
    Request body:
    {
        "to_address": "recipient@example.com",
        "subject": "Subject line",
        "body": "Email body (HTML or plain text)",
        "in_reply_to": 123,  // Optional: StoredEmail ID if replying
        "ai_generated": false  // Optional: whether this was AI-generated
    }
    """
    try:
        data = request.json or {}
        
        # Validate
        required = ['to_address', 'subject', 'body']
        if not all(k in data for k in required):
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {required}"
            }), 400
        
        # Send email
        if send_email_smtp(data['to_address'], data['subject'], data['body'], 
                          cc_address=data.get('cc_address'), 
                          bcc_address=data.get('bcc_address')):
            # Create SentEmail record
            try:
                sent = SentEmail(
                    to_address=data['to_address'],
                    cc_address=data.get('cc_address'),
                    bcc_address=data.get('bcc_address'),
                    subject=data['subject'],
                    body=data['body'],
                    html_body=data.get('html_body'),
                    in_reply_to=data.get('in_reply_to'),
                    ai_generated=data.get('ai_generated', False),
                    status='sent'
                )
                db.session.add(sent)
                db.session.commit()
                logger.info(f"Tracked sent email to {data['to_address']}")
            except Exception as e:
                logger.warning(f"Could not track sent email: {e}")
            
            return jsonify({
                "success": True,
                "message": f"Email sent to {data['to_address']}"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Failed to send email"
            }), 500
    
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@extra_email_bp.route('/drafts/<int:draft_id>/send', methods=['POST'])
@require_auth
def send_draft(draft_id):
    """Send a draft email and track it in sent emails."""
    try:
        draft = DraftEmail.query.get(draft_id)
        if not draft:
            return jsonify({"success": False, "error": "Draft not found"}), 404
        
        # Send the email
        if send_email_smtp(draft.to_address, draft.subject, draft.body or draft.html_body,
                          cc_address=draft.cc_address, bcc_address=draft.bcc_address):
            # Create SentEmail record
            try:
                sent = SentEmail(
                    to_address=draft.to_address,
                    cc_address=draft.cc_address,
                    bcc_address=draft.bcc_address,
                    subject=draft.subject,
                    body=draft.body,
                    html_body=draft.html_body,
                    in_reply_to=draft.in_reply_to,
                    from_draft=draft_id,
                    ai_generated=draft.auto_generated,
                    ai_context=draft.ai_prompt,
                    status='sent'
                )
                db.session.add(sent)
            except Exception as e:
                logger.warning(f"Could not create SentEmail record: {e}")
            
            # Update draft status
            draft.status = 'sent'
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Draft sent successfully"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Failed to send email"
            }), 500
    
    except Exception as e:
        logger.error(f"Error sending draft: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# CONTINUOUS EMAIL SYNC & AUTO-REPLY ENDPOINTS
# ============================================================================

@extra_email_bp.route('/sync-all', methods=['POST'])
@require_auth
def sync_all_emails():
    """
    Perform a one-time full sync of all emails from the last 30 days.
    This downloads all emails (read and unread) and stores them in the database.
    
    Request body (optional):
    {
        "days_back": 30,  // How far back to sync (default: 30)
        "limit": 500      // Max emails to download (default: 500)
    }
    """
    try:
        data = request.json or {}
        days_back = data.get('days_back', 30)
        limit = data.get('limit', 500)
        
        logger.info(f"🔄 Performing full email sync from last {days_back} days...")
        
        email_service = EmailConfig.get_email_service()
        if not email_service:
            return jsonify({
                "success": False,
                "error": "Email service not configured"
            }), 400
        
        try:
            emails = email_service.get_emails_by_date_range(days_back=days_back, limit=limit)
            logger.info(f"✓ Retrieved {len(emails)} emails")
        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}")
            return jsonify({"success": False, "error": str(e)}), 400
        finally:
            email_service.disconnect()
        
        # Store in database
        new_count = 0
        for email in emails:
            try:
                existing = StoredEmail.query.filter_by(email_uid=email['id']).first()
                if not existing:
                    received_dt = datetime.fromisoformat(email['date']) if email.get('date') else datetime.now()
                    
                    stored_email = StoredEmail(
                        email_uid=email['id'],
                        from_address=email.get('from', ''),
                        subject=email.get('subject', ''),
                        body=email.get('text', ''),
                        html_body=email.get('html', ''),
                        received_date=received_dt,
                        is_read=not email.get('is_unread', False),
                        folder='INBOX'
                    )
                    db.session.add(stored_email)
                    new_count += 1
            except Exception as e:
                logger.error(f"Error processing email: {e}")
        
        if new_count > 0:
            db.session.commit()
        
        logger.info(f"✓ Synced {new_count} new emails, {len(emails) - new_count} already existed")
        
        return jsonify({
            "success": True,
            "message": f"Synced {len(emails)} emails, stored {new_count} new",
            "total_downloaded": len(emails),
            "new_emails": new_count
        }), 200
    
    except Exception as e:
        logger.error(f"Error in sync_all_emails: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@extra_email_bp.route('/sync/start', methods=['POST'])
@require_auth
def start_continuous_sync():
    """Start continuous background email syncing (like Outlook auto-sync)."""
    try:
        from ..email_sync_service import start_continuous_sync as sync_start
        return sync_start()
    except Exception as e:
        logger.error(f"Error in start_continuous_sync: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@extra_email_bp.route('/sync/stop', methods=['POST'])
@require_auth
def stop_continuous_sync():
    """Stop continuous background email syncing."""
    try:
        from ..email_sync_service import stop_continuous_sync as sync_stop
        return sync_stop()
    except Exception as e:
        logger.error(f"Error in stop_continuous_sync: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@extra_email_bp.route('/sync/status', methods=['GET'])
@require_auth
def get_sync_status():
    """Get current email sync status."""
    try:
        from ..email_sync_service import get_sync_status as get_status
        status = get_status()
        return jsonify({
            "success": True,
            "sync_status": status
        }), 200
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@extra_email_bp.route('/auto-reply/apply-new', methods=['POST'])
@require_auth
def apply_auto_reply_to_new():
    """
    Apply auto-reply to all new unread emails using AI.
    Only replies to emails that haven't been read yet (new emails).
    
    Request body (optional):
    {
        "limit": 10,  // Max emails to reply to (default: 10)
        "ai_instructions": "Custom instructions for AI response"
    }
    """
    try:
        data = request.json or {}
        
        # Get auto-reply settings
        settings = AutoReplySettings.query.first()
        if not settings or not settings.enabled:
            return jsonify({
                "success": False,
                "error": "Auto-reply not enabled"
            }), 400
        
        # Prepare config
        auto_reply_config = {
            'limit': data.get('limit', 10),
            'ai_instructions': data.get('ai_instructions') or settings.ai_instructions
        }
        
        from ..email_sync_service import apply_auto_reply_to_new_emails
        result = apply_auto_reply_to_new_emails(auto_reply_config)
        
        if result.get('status') == 'success':
            return jsonify({
                "success": True,
                **result
            }), 200
        else:
            return jsonify({
                "success": False,
                **result
            }), 500
    
    except Exception as e:
        logger.error(f"Error applying auto-reply: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
        if draft:
            draft.status = 'failed'
            draft.error_message = str(e)
            db.session.commit()
        
        return jsonify({"success": False, "error": str(e)}), 500
