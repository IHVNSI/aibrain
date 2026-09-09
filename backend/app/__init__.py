"""Flask application factory for assistantai."""
import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy import text

from .config import Config
from .extensions import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Setup file-based logging for server logs
from .log_manager import setup_log_file_handler
try:
    setup_log_file_handler()
except Exception as e:
    logger.warning(f"Could not setup file logging: {e}")


def create_app() -> Flask:
    # Configure Flask with static folder support for Swagger UI assets
    app = Flask(
        __name__,
        static_folder="static",
        static_url_path="/static"
    )
    app.config["SECRET_KEY"] = Config.SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = Config.ADMIN_DB_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app)

    # Import models so SQLAlchemy registers them, then create tables.
    from . import models  # noqa: F401
    with app.app_context():
        db.create_all()
        # Lightweight schema evolution for SQLite-only deployments without migrations.
        try:
            logger.info("🔄 Starting schema evolution check...")
            # Check if conversations table exists and has required columns
            inspector_result = db.session.execute(text("PRAGMA table_info(conversations)")).fetchall()
            col_names = {c[1] for c in inspector_result}
            logger.info(f"📋 Conversations table columns: {col_names}")
            
            if "user_id" not in col_names:
                logger.info("➕ Adding user_id column to conversations table...")
                db.session.execute(text("ALTER TABLE conversations ADD COLUMN user_id INTEGER"))
                db.session.commit()
                logger.info("✅ Added user_id column to conversations table")
            else:
                logger.info("✅ user_id column already exists in conversations table")
            
            if "is_shared" not in col_names:
                logger.info("➕ Adding is_shared column to conversations table...")
                db.session.execute(text("ALTER TABLE conversations ADD COLUMN is_shared BOOLEAN DEFAULT 0"))
                db.session.commit()
                logger.info("✅ Added is_shared column to conversations table")
            else:
                logger.info("✅ is_shared column already exists in conversations table")
            
            # Evolve training_items table
            cols = db.session.execute(text("PRAGMA table_info(training_items)")).fetchall()
            col_names = {c[1] for c in cols}
            if "rule" not in col_names:
                db.session.execute(text("ALTER TABLE training_items ADD COLUMN rule VARCHAR(20) DEFAULT 'optional'"))
            if "access" not in col_names:
                db.session.execute(text("ALTER TABLE training_items ADD COLUMN access VARCHAR(20) DEFAULT 'all'"))
            if "source_kind" not in col_names:
                db.session.execute(text("ALTER TABLE training_items ADD COLUMN source_kind VARCHAR(40) DEFAULT 'manual'"))
            if "source_name" not in col_names:
                db.session.execute(text("ALTER TABLE training_items ADD COLUMN source_name VARCHAR(255)"))
            if "source_file_type" not in col_names:
                db.session.execute(text("ALTER TABLE training_items ADD COLUMN source_file_type VARCHAR(40)"))
                db.session.commit()
            
            # Evolve audit_logs table - add user_id column if missing
            audit_cols = db.session.execute(text("PRAGMA table_info(audit_logs)")).fetchall()
            audit_col_names = {c[1] for c in audit_cols}
            if "user_id" not in audit_col_names:
                logger.info("➕ Adding user_id column to audit_logs table...")
                db.session.execute(text("ALTER TABLE audit_logs ADD COLUMN user_id INTEGER"))
                db.session.commit()
                logger.info("✅ Added user_id column to audit_logs table")
            else:
                logger.info("✅ user_id column already exists in audit_logs table")
            
            if "is_api" not in audit_col_names:
                logger.info("➕ Adding is_api column to audit_logs table...")
                db.session.execute(text("ALTER TABLE audit_logs ADD COLUMN is_api BOOLEAN DEFAULT 0"))
                db.session.commit()
                logger.info("✅ Added is_api column to audit_logs table")
            else:
                logger.info("✅ is_api column already exists in audit_logs table")
            
            # Evolve auth_config table - add company_type_field column if missing
            auth_config_cols = db.session.execute(text("PRAGMA table_info(auth_config)")).fetchall()
            auth_config_col_names = {c[1] for c in auth_config_cols}
            if "company_type_field" not in auth_config_col_names:
                logger.info("➕ Adding company_type_field column to auth_config table...")
                db.session.execute(text("ALTER TABLE auth_config ADD COLUMN company_type_field VARCHAR(255)"))
                db.session.commit()
                logger.info("✅ Added company_type_field column to auth_config table")
            else:
                logger.info("✅ company_type_field column already exists in auth_config table")
            
            # Evolve audit_logs table - add username and role_name columns
            if "username" not in audit_col_names:
                logger.info("➕ Adding username column to audit_logs table...")
                db.session.execute(text("ALTER TABLE audit_logs ADD COLUMN username VARCHAR(255)"))
                db.session.commit()
                logger.info("✅ Added username column to audit_logs table")
            else:
                logger.info("✅ username column already exists in audit_logs table")
            
            if "role_name" not in audit_col_names:
                logger.info("➕ Adding role_name column to audit_logs table...")
                db.session.execute(text("ALTER TABLE audit_logs ADD COLUMN role_name VARCHAR(255)"))
                db.session.commit()
                logger.info("✅ Added role_name column to audit_logs table")
            else:
                logger.info("✅ role_name column already exists in audit_logs table")
            
            # Evolve users table - add assigned_branches column if missing
            users_cols = db.session.execute(text("PRAGMA table_info(users)")).fetchall()
            users_col_names = {c[1] for c in users_cols}
            if "assigned_branches" not in users_col_names:
                logger.info("➕ Adding assigned_branches column to users table...")
                db.session.execute(text("ALTER TABLE users ADD COLUMN assigned_branches TEXT DEFAULT NULL"))
                db.session.commit()
                logger.info("✅ Added assigned_branches column to users table")
            else:
                logger.info("✅ assigned_branches column already exists in users table")
            
            # Initialize table-role access if needed
            from .models import TableRoleAccess, Role
            roles_exist = Role.query.count() > 0
            access_mappings_exist = TableRoleAccess.query.count() > 0
            
            if roles_exist and not access_mappings_exist:
                logger.info("🔄 Initializing table-role access (first run)...")
                try:
                    from sqlalchemy import create_engine, inspect
                    
                    db_url = Config.SOURCE_DB_URL
                    if db_url:
                        engine = create_engine(db_url)
                        inspector = inspect(engine)
                        table_names = [t for t in inspector.get_table_names() 
                                      if not t.startswith('sqlite_') and t not in ['alembic_version']]
                        
                        roles = Role.query.all()
                        initialized_count = 0
                        
                        for table_name in table_names:
                            for role in roles:
                                existing = TableRoleAccess.query.filter_by(
                                    table_name=table_name, 
                                    role_id=role.id
                                ).first()
                                
                                if not existing:
                                    access = TableRoleAccess(table_name=table_name, role_id=role.id)
                                    db.session.add(access)
                                    initialized_count += 1
                        
                        if initialized_count > 0:
                            db.session.commit()
                            logger.info(f"✅ Initialized table-role access: {len(table_names)} tables × {len(roles)} roles")
                except Exception as init_error:
                    logger.warning(f"⚠️  Could not auto-initialize table-role access: {init_error}")
                    db.session.rollback()
            elif roles_exist and access_mappings_exist:
                # Auto-sync new tables: Grant all roles access to any newly added tables
                logger.info("🔄 Syncing new tables for role access...")
                try:
                    from sqlalchemy import create_engine, inspect
                    
                    db_url = Config.SOURCE_DB_URL
                    if db_url:
                        engine = create_engine(db_url)
                        inspector = inspect(engine)
                        table_names = [t for t in inspector.get_table_names() 
                                      if not t.startswith('sqlite_') and t not in ['alembic_version']]
                        
                        roles = Role.query.all()
                        synced_count = 0
                        
                        for table_name in table_names:
                            for role in roles:
                                existing = TableRoleAccess.query.filter_by(
                                    table_name=table_name, 
                                    role_id=role.id
                                ).first()
                                
                                if not existing:
                                    access = TableRoleAccess(table_name=table_name, role_id=role.id)
                                    db.session.add(access)
                                    synced_count += 1
                        
                        if synced_count > 0:
                            db.session.commit()
                            logger.info(f"✅ Synced {synced_count} new table-role access records")
                except Exception as sync_error:
                    logger.warning(f"⚠️  Could not sync table-role access for new tables: {sync_error}")
                    db.session.rollback()
        except Exception as e:
            logger.error(f"❌ Schema evolution error: {type(e).__name__}: {e}")
            db.session.rollback()

        # Initialize AI Context if not exists
        try:
            from .models import AIContext
            from .response_guide import CLIENTSHOT_SYSTEM_INSTRUCTIONS
            
            existing_context = AIContext.query.filter_by(is_active=True).first()
            if not existing_context:
                logger.info("🤖 Initializing AI Context with default instructions...")
                default_context = AIContext(
                    name='default',
                    is_active=True,
                    system_instructions=CLIENTSHOT_SYSTEM_INSTRUCTIONS,
                    response_rules='',
                    business_rules='',
                    data_isolation_rules='',
                    vocabulary=''
                )
                db.session.add(default_context)
                db.session.commit()
                logger.info("✅ AI Context initialized successfully")
            else:
                logger.info("✅ AI Context already exists")
        except Exception as e:
            logger.warning(f"⚠️  Could not initialize AI Context: {e}")
            db.session.rollback()

    # Register blueprints
    from .api.chat import chat_bp
    from .api.multiperson_chat import multiperson_bp
    from .api.conversations import conversations_bp
    from .api.settings import settings_bp
    from .api.training import training_bp
    from .api.cache import cache_bp
    from .api.data_exchange import data_exchange_bp
    from .api.auth import auth_bp, seed_defaults
    from .api.auth_config import auth_config_bp
    from .api.security import security_bp
    from .api.system import system_bp
    from .api.email_scheduling import email_bp, scheduler_bp, initialize_email_handlers, get_task_scheduler
    from .api.voice import voice_bp

    app.register_blueprint(chat_bp)
    app.register_blueprint(multiperson_bp)
    app.register_blueprint(conversations_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(training_bp)
    app.register_blueprint(cache_bp)
    app.register_blueprint(data_exchange_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(auth_config_bp)
    app.register_blueprint(security_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(scheduler_bp)
    app.register_blueprint(voice_bp)

    # Seed default roles + admin user + restricted commands.
    with app.app_context():
        seed_defaults()

    @app.route("/api")
    def api_root():
        """Root API endpoint - redirect to documentation."""
        from flask import redirect
        return redirect("/api/docs/", code=302)

    @app.route("/api/health")
    def health():
        from .vanna_service import get_vanna_service
        return jsonify({"status": "ok", "engine": get_vanna_service().status()})

    # Interactive API documentation (Swagger UI at /api/docs/, spec at /api/openapi.json).
    try:
        from .api.openapi import init_swagger
        init_swagger(app)
        logger.info("📚 Swagger UI available at /api/docs/")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Swagger UI not mounted: {exc}")

    # Best-effort: initialize the text-to-SQL engine on startup (non-fatal).
    with app.app_context():
        try:
            from .bootstrap import reinitialize_vanna
            status = reinitialize_vanna()
            logger.info(f"Engine startup status: {status}")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Engine startup deferred (configure in Settings): {exc}")

    logger.info("✅ assistantai backend ready")
    return app
