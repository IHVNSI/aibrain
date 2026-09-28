"""Email continuous sync and auto-reply implementation."""
import logging
import threading
import time
import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from .extensions import db
from .auth import require_auth
from .email_service import EmailConfig
from .models import StoredEmail, EmailSyncStatus, AutoReplySettings, DraftEmail
from .llm.factory import build_llm

logger = logging.getLogger(__name__)

# Global state for continuous sync
_sync_thread = None
_sync_active = False
_sync_lock = threading.Lock()


def get_or_create_sync_status():
    """Get or create sync status record."""
    status = EmailSyncStatus.query.first()
    if not status:
        status = EmailSyncStatus(
            sync_type='incremental',
            status='pending',
            total_emails_synced=0,
            new_emails_count=0
        )
        db.session.add(status)
        db.session.commit()
    return status


def get_sync_status_response():
    """Get current sync status as response dict."""
    status = get_or_create_sync_status()
    new_emails = StoredEmail.query.filter_by(is_new=True).count()
    total_emails = StoredEmail.query.count()
    
    return {
        "syncing": _sync_active,
        "status": status.status,
        "sync_type": status.sync_type,
        "last_sync_time": status.last_sync_time.isoformat() if status.last_sync_time else None,
        "next_sync_time": status.next_sync_time.isoformat() if status.next_sync_time else None,
        "total_emails": total_emails,
        "new_emails_count": new_emails,
        "emails_in_last_sync": status.emails_in_last_sync,
        "sync_duration_seconds": status.sync_duration_seconds,
        "error_message": status.error_message,
        "timestamp": datetime.utcnow().isoformat()
    }


@require_auth
def start_full_sync():
    """Start full email sync (download all emails from all folders)."""
    try:
        # Create or update sync status
        status = get_or_create_sync_status()
        status.status = 'in_progress'
        status.sync_type = 'full'
        status.sync_started_at = datetime.utcnow()
        db.session.commit()
        
        logger.info("Starting full email sync...")
        
        # Start sync in background thread
        sync_thread = threading.Thread(target=_full_sync_worker, daemon=True)
        sync_thread.start()
        
        return jsonify({
            "success": True,
            "message": "Full email sync started (background)",
            "status": get_sync_status_response()
        }), 200
    
    except Exception as e:
        logger.error(f"Error starting full sync: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def _full_sync_worker():
    """Background worker for full email sync."""
    try:
        from .email_intelligence import EmailProcessor, SenderDetector
        
        status = get_or_create_sync_status()
        start_time = datetime.utcnow()
        
        # Get email service
        email_service = EmailConfig.get_email_service()
        if not email_service:
            logger.error("Email service not configured")
            status.status = 'failed'
            status.error_message = "Email service not configured"
            db.session.commit()
            return
        
        try:
            # Get all folders
            folders = email_service.get_folder_list()
            logger.info(f"Found {len(folders)} folders to sync")
            
            total_new = 0
            total_processed = 0
            synced_folders = []
            
            # Get auto-reply settings
            auto_reply_settings = None
            try:
                reply_settings = AutoReplySettings.query.first()
                if reply_settings and reply_settings.enabled:
                    # Convert model to dict with expected fields
                    # mode: 'auto' (send immediately) or 'review' (create drafts)
                    auto_reply_settings = {
                        'enabled': reply_settings.enabled,
                        'auto_send': reply_settings.mode == 'auto',  # True if mode is 'auto', False if 'review'
                        'use_llm': False,  # Using template-based for now
                        'enabled_for_sender_types': ['client', 'vendor'],  # Default to client and vendor
                        'exclude_sender_types': ['admin', 'support'],  # Don't auto-reply to system emails
                    }
                    logger.info(f"Auto-reply enabled: mode={reply_settings.mode}")
            except Exception as e:
                logger.warning(f"Could not load auto-reply settings: {e}")
            
            # Sync each folder
            for folder in folders:
                try:
                    logger.info(f"Syncing folder: {folder}")
                    # Fetch ALL emails from folder (both read and unread)
                    emails = email_service.get_all_emails(folder, limit=1000)
                    logger.info(f"Retrieved {len(emails)} total emails from {folder}")
                    
                    folder_new_count = 0
                    for email_data in emails:
                        # Check if email already exists
                        existing = StoredEmail.query.filter_by(email_uid=email_data['id']).first()
                        if not existing:
                            received_dt = datetime.fromisoformat(email_data['date']) if email_data.get('date') else datetime.now()
                            
                            stored_email = StoredEmail(
                                email_uid=email_data['id'],
                                from_address=email_data.get('from', ''),
                                subject=email_data.get('subject', ''),
                                body=email_data.get('text', ''),
                                html_body=email_data.get('html', ''),
                                received_date=received_dt,
                                is_read=not email_data.get('is_unread', False),
                                folder=folder,
                                is_new=True
                            )
                            db.session.add(stored_email)
                            db.session.flush()  # Flush to get the ID
                            
                            # Process the email for sender detection and auto-response
                            if stored_email.id:
                                try:
                                    process_result = EmailProcessor.process_incoming_email(
                                        stored_email,
                                        auto_reply_settings,
                                        use_drafts=True  # Create drafts for review
                                    )
                                    
                                    total_processed += 1
                                    
                                    # Log processing result
                                    logger.info(f"Email {stored_email.id}: {process_result['sender_type']} | "
                                              f"Draft: {process_result['draft_created']} | "
                                              f"AutoSent: {process_result['auto_sent']}")
                                    
                                except Exception as proc_error:
                                    logger.error(f"Error processing email {stored_email.id}: {proc_error}")
                            
                            folder_new_count += 1
                    
                    if folder_new_count > 0:
                        db.session.commit()
                        logger.info(f"Synced {folder_new_count} new emails from {folder}")
                        total_new += folder_new_count
                    
                    synced_folders.append(folder)
                except Exception as e:
                    logger.error(f"Error syncing folder {folder}: {e}", exc_info=True)
                    db.session.rollback()
            
            # Update sync status
            status.status = 'completed'
            status.last_sync_time = datetime.utcnow()
            status.next_sync_time = datetime.utcnow() + timedelta(minutes=int(os.getenv('EMAIL_CHECK_INTERVAL', '5')))
            status.emails_in_last_sync = total_new
            status.total_emails_synced = StoredEmail.query.count()
            status.new_emails_count = StoredEmail.query.filter_by(is_new=True).count()
            status.folders_synced = json.dumps(synced_folders)
            status.error_message = None
            status.sync_duration_seconds = int((datetime.utcnow() - start_time).total_seconds())
            db.session.commit()
            
            logger.info(f"Full sync completed: {total_new} new emails, {total_processed} processed, {len(synced_folders)} folders")
        
        finally:
            try:
                email_service.disconnect()
            except:
                pass
    
    except Exception as e:
        logger.error(f"Error in full sync worker: {e}", exc_info=True)
        status = get_or_create_sync_status()
        status.status = 'failed'
        status.error_message = str(e)
        db.session.commit()


@require_auth
def start_continuous_sync():
    """Start continuous email syncing in background."""
    global _sync_thread, _sync_active
    
    try:
        with _sync_lock:
            if _sync_active:
                return jsonify({
                    "success": False,
                    "message": "Sync already running"
                }), 400
            
            # Start background sync thread
            _sync_thread = threading.Thread(target=_continuous_sync_worker, daemon=True)
            _sync_thread.start()
            _sync_active = True
            
            logger.info("Continuous email sync started")
            return jsonify({
                "success": True,
                "message": "Continuous email sync started",
                "status": get_sync_status_response()
            }), 200
    
    except Exception as e:
        logger.error(f"Error starting continuous sync: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@require_auth
def stop_continuous_sync():
    """Stop continuous email syncing."""
    global _sync_active
    
    try:
        with _sync_lock:
            _sync_active = False
            logger.info("Continuous email sync stopped")
        
        return jsonify({
            "success": True,
            "message": "Continuous email sync stopped",
            "status": get_sync_status_response()
        }), 200
    
    except Exception as e:
        logger.error(f"Error stopping continuous sync: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def _continuous_sync_worker():
    """Background worker that continuously syncs emails."""
    global _sync_active
    
    try:
        from ..socket_events import broadcast_email_event
    except:
        broadcast_email_event = None
    
    sync_interval = int(os.getenv('EMAIL_CHECK_INTERVAL', '1')) * 60  # Convert to seconds
    
    while _sync_active:
        try:
            # Get last sync time for incremental sync
            status = get_or_create_sync_status()
            last_sync = status.last_sync_time or (datetime.utcnow() - timedelta(hours=24))
            
            logger.info(f"Syncing new emails since {last_sync}...")
            
            # Get email service
            email_service = EmailConfig.get_email_service()
            if not email_service:
                logger.warning("Email service not configured")
                time.sleep(sync_interval)
                continue
            
            try:
                # Get new emails since last sync
                new_emails = email_service.get_emails_after_date(last_sync, 'INBOX', limit=100)
                logger.info(f"Retrieved {len(new_emails)} new emails")
            except Exception as e:
                logger.error(f"Failed to fetch emails: {e}")
                time.sleep(sync_interval)
                continue
            finally:
                try:
                    email_service.disconnect()
                except:
                    pass
            
            # Store new emails in database
            stored_count = 0
            new_email_ids = []
            
            for email in new_emails:
                try:
                    # Check if email already exists
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
                            folder='INBOX',
                            is_new=True
                        )
                        db.session.add(stored_email)
                        stored_count += 1
                        new_email_ids.append(email['id'])
                        
                        # Broadcast new email to WebSocket clients
                        if broadcast_email_event:
                            try:
                                broadcast_email_event('new_email', {
                                    'id': email['id'],
                                    'from': email.get('from'),
                                    'subject': email.get('subject'),
                                    'date': email.get('date'),
                                    'preview': email.get('text', '')[:100] if email.get('text') else ''
                                })
                            except Exception as e:
                                logger.error(f"Error broadcasting email: {e}")
                except Exception as e:
                    logger.error(f"Error processing email: {e}")
            
            if stored_count > 0:
                try:
                    db.session.commit()
                    logger.info(f"Stored {stored_count} new emails in database")
                    
                    # Update sync status
                    status.last_sync_time = datetime.utcnow()
                    status.emails_in_last_sync = stored_count
                    status.total_emails_synced = StoredEmail.query.count()
                    status.new_emails_count = StoredEmail.query.filter_by(is_new=True).count()
                    db.session.commit()
                    
                    # AUTO-REPLY: Process new unread emails with AI
                    logger.info(f"Processing {stored_count} new emails for auto-reply...")
                    auto_reply_settings = AutoReplySettings.query.first()
                    if auto_reply_settings and auto_reply_settings.enabled:
                        auto_reply_config = {
                            'mode': auto_reply_settings.mode,  # 'auto' or 'review'
                            'ai_instructions': auto_reply_settings.ai_instructions or 'Provide a professional, helpful response.',
                            'use_database': auto_reply_settings.use_database,
                            'limit': 10  # Process up to 10 new emails per sync
                        }
                        reply_result = apply_auto_reply_to_new_emails(auto_reply_config)
                        logger.info(f"Auto-reply result: {reply_result}")
                    else:
                        logger.debug("Auto-reply not enabled")
                    
                    # Broadcast sync completion
                    if broadcast_email_event:
                        broadcast_email_event('emails_synced', {
                            'new_count': stored_count,
                            'timestamp': datetime.utcnow().isoformat()
                        })
                except Exception as e:
                    logger.error(f"Error committing emails: {e}")
                    db.session.rollback()
            
            # Wait for next sync interval
            time.sleep(sync_interval)
        
        except Exception as e:
            logger.error(f"Error in sync worker: {e}", exc_info=True)
            time.sleep(60)  # Wait 1 minute before retrying


def apply_auto_reply_to_new_emails(auto_reply_config):
    """Apply auto-reply to NEW unread emails with AI and ACTUAL DATABASE DATA."""
    try:
        # Get only new emails that haven't been auto-replied to yet
        new_emails = StoredEmail.query.filter_by(
            is_new=True,
            is_read=False,
            auto_reply_sent=False
        ).limit(auto_reply_config.get('limit', 10)).all()
        
        if not new_emails:
            logger.info("No new unread emails for auto-reply")
            return {"status": "success", "count": 0, "message": "No new emails to reply to"}
        
        # Get LLM
        llm = build_llm()
        if not llm:
            logger.warning("LLM not configured")
            return {"status": "error", "message": "LLM not configured"}
        
        replied_count = 0
        draft_count = 0
        
        for stored_email in new_emails:
            try:
                # Build ACTUAL database context (execute SQL queries like manual version)
                database_data = ""
                fetched_rows = []
                fetched_columns = []
                generated_sql = ""
                
                if auto_reply_config.get('use_database'):
                    try:
                        from .vanna_service import get_vanna_service
                        vanna = get_vanna_service()
                        
                        if vanna and vanna.ready:
                            email_content = f"{stored_email.subject}\n{stored_email.body or ''}"
                            
                            logger.info(f"🔍 Attempting to fetch database data for email from {stored_email.from_address}")
                            
                            # Step 1: Generate SQL from email content
                            try:
                                history = []
                                generated_sql = vanna.generate_sql_multiturn(email_content, history)
                                
                                if generated_sql and generated_sql.strip().upper().startswith('SELECT'):
                                    logger.info(f"✓ Generated SQL: {generated_sql[:80]}...")
                                    
                                    # Step 2: Execute SQL to get actual data
                                    try:
                                        df = vanna.run_sql(generated_sql)
                                        
                                        if df is not None and len(df) > 0:
                                            columns = list(df.columns)
                                            rows = df.head(500).to_dict(orient="records")
                                            
                                            # Convert to serializable format
                                            from .api.chat import _convert_rows_to_serializable
                                            rows = _convert_rows_to_serializable(rows)
                                            
                                            fetched_rows = rows[:20]  # Limit to 20 rows
                                            fetched_columns = columns
                                            
                                            # Format data naturally for email response
                                            database_data = "\n\nRELEVANT INFORMATION FROM OUR RECORDS:\n"
                                            database_data += "-" * 50 + "\n"
                                            
                                            for i, row in enumerate(fetched_rows[:10], 1):
                                                for col, value in row.items():
                                                    nice_col = col.replace('_', ' ').title()
                                                    database_data += f"{nice_col}: {value}\n"
                                                if i < len(fetched_rows[:10]):
                                                    database_data += "-" * 50 + "\n"
                                            
                                            logger.info(f"✓ Fetched {len(fetched_rows)} rows from database")
                                    
                                    except Exception as e:
                                        logger.warning(f"Could not execute SQL: {e}")
                                        database_data = f"\nNote: Database query attempted but could not retrieve data: {str(e)[:100]}"
                            
                            except Exception as e:
                                logger.debug(f"Could not generate SQL: {e}")
                    
                    except Exception as e:
                        logger.debug(f"Could not fetch database data: {e}")
                
                # Build training data context for additional guidance
                training_context = ""
                try:
                    from .models import TrainingItem, AIContext
                    training_items = TrainingItem.query.limit(5).all()
                    if training_items:
                        training_context = "\n\nSystem Guidance and Context:\n"
                        for item in training_items:
                            if item.content and len(item.content) < 500:
                                training_context += f"- {item.content[:200]}\n"
                    
                    # Get AI context for system instructions
                    ai_context = AIContext.get_active()
                    if ai_context and ai_context.system_instructions:
                        training_context += f"\n\nSystem Instructions:\n{ai_context.system_instructions}\n"
                except Exception as e:
                    logger.debug(f"Could not fetch training context: {e}")
                
                # Generate AI response WITH ACTUAL database data
                prompt = f"""You are a professional email assistant responding on behalf of the user.

The user received this email:

From: {stored_email.from_address}
Subject: {stored_email.subject}

Body:
{stored_email.body or stored_email.html_body}

{f'RELEVANT DATA TO REFERENCE:{database_data}' if database_data else ''}

{training_context}

Guidelines for Response:
{auto_reply_config.get('ai_instructions', 'Please generate a professional, helpful response.')}
- Address the sender's specific points
- Be concise and professional
- Use the data naturally in your response (don't mention where it came from)
- If data is available, incorporate it into the conversation

Only return the email body with greeting and closing, no subject line or metadata."""
                
                messages = [{"role": "user", "content": prompt}]
                response_text = llm.chat(messages)
                
                if response_text:
                    # Apply HTML formatting to the response
                    from .api.email_extra import convert_text_to_html_email
                    plain_text_body, html_body = convert_text_to_html_email(response_text, stored_email.from_address)
                    
                    subject = f"Re: {stored_email.subject}"
                    
                    if auto_reply_config.get('mode') == 'auto':
                        # Send immediately with HTML formatting
                        try:
                            from .email_scheduling import send_email_smtp
                            if send_email_smtp(stored_email.from_address, subject, html_body or plain_text_body):
                                stored_email.auto_reply_sent = True
                                stored_email.is_new = False  # Mark as processed
                                db.session.commit()
                                replied_count += 1
                                logger.info(f"✅ Auto-reply sent to {stored_email.from_address} (Subject: {subject[:50]})")
                            else:
                                logger.warning(f"Failed to send auto-reply to {stored_email.from_address}")
                        except Exception as e:
                            logger.error(f"Error sending auto-reply: {e}")
                    else:
                        # Save as draft for review with HTML formatting
                        try:
                            draft = DraftEmail(
                                to_address=stored_email.from_address,
                                subject=subject,
                                body=plain_text_body,
                                html_body=html_body,
                                status='pending_review',
                                in_reply_to=stored_email.id,
                                auto_generated=True,
                                ai_prompt=prompt
                            )
                            db.session.add(draft)
                            stored_email.is_new = False  # Mark as processed
                            db.session.commit()
                            draft_count += 1
                            logger.info(f"📝 Auto-reply draft created for {stored_email.from_address} (with database data, review required)")
                        except Exception as e:
                            logger.error(f"Error creating draft: {e}")
                            db.session.rollback()
                
            except Exception as e:
                logger.error(f"Error processing email from {stored_email.from_address}: {e}", exc_info=True)
        
        return {
            "status": "success",
            "count": replied_count + draft_count,
            "auto_sent": replied_count,
            "pending_review": draft_count,
            "message": f"Processed {replied_count} auto-sent + {draft_count} pending review (all with database data)"
        }
        
    except Exception as e:
        logger.error(f"Error in apply_auto_reply_to_new_emails: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
