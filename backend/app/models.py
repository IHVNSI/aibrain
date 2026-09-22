"""SQLite-backed models: settings, conversations, audit, Vanna training metadata."""
import json
from datetime import datetime

from .extensions import db


# --------------------------------------------------------------------------- #
# Auth / multi-tenant models (mirrors brainz: company + branches + roles)
# --------------------------------------------------------------------------- #
class Company(db.Model):
    __tablename__ = "companies"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    company_code = db.Column(db.String(100), nullable=True)  # Unique identifier (from token)
    company_type = db.Column(db.String(50), default="PARENT_COMPANY")  # PARENT_COMPANY | WORKSPACE | BRANCH
    parent_company_fk = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=True)  # For BRANCH type
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "company_code": self.company_code,
            "company_type": self.company_type, "parent_company_fk": self.parent_company_fk,
            "is_active": self.is_active,
        }

    def get_company_fk(self):
        """
        Get the foreign key for data filtering.
        - If BRANCH: return parent_company_fk
        - Otherwise: return self.id
        """
        if self.company_type == "BRANCH" and self.parent_company_fk:
            return self.parent_company_fk
        return self.id


# Many-to-many association table for users and companies
user_companies = db.Table(
    "user_companies",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("company_id", db.Integer, db.ForeignKey("companies.id"), primary_key=True),
    db.Column("user_role", db.String(50)),
    db.Column("joined_at", db.DateTime, default=datetime.utcnow),
)


class Branch(db.Model):
    __tablename__ = "branches"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "company_id": self.company_id, "name": self.name,
            "location": self.location, "is_active": self.is_active,
        }


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False)  # admins bypass company/branch scoping
    is_system_role = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "is_admin": self.is_admin, "is_system_role": self.is_system_role,
        }


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=True)
    assigned_branches = db.Column(db.Text, nullable=True, default=None)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_roles = db.relationship("UserRole", backref="user", lazy=True, cascade="all, delete-orphan")
    company = db.relationship("Company", foreign_keys=[company_id])
    branch = db.relationship("Branch", foreign_keys=[branch_id])
    companies = db.relationship("Company", secondary=user_companies, backref=db.backref("assigned_users", lazy=True))

    def roles(self):
        out = []
        for ur in self.user_roles:
            role = Role.query.get(ur.role_id)
            if role:
                out.append(role)
        return out

    def is_admin(self):
        return any(r.is_admin for r in self.roles())

    def to_dict(self):
        import json
        roles = self.roles()
        assigned_branches = self.assigned_branches
        if assigned_branches and isinstance(assigned_branches, str):
            try:
                assigned_branches = json.loads(assigned_branches)
            except:
                assigned_branches = []
        return {
            "id": self.id, "username": self.username, "email": self.email,
            "first_name": self.first_name, "last_name": self.last_name,
            "company_id": self.company_id, "branch_id": self.branch_id,
            "company_name": self.company.name if self.company else None,
            "branch_name": self.branch.name if self.branch else None,
            "assigned_branches": assigned_branches,
            "is_active": self.is_active,
            "roles": [r.name for r in roles],
            "is_admin": any(r.is_admin for r in roles),
        }

class UserRole(db.Model):
    __tablename__ = "user_roles"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "role_id", name="uq_user_role"),)


class RestrictedSQLCommand(db.Model):
    """Restricted SQL commands/keywords configured in the Security tab."""
    __tablename__ = "restricted_sql_commands"
    id = db.Column(db.Integer, primary_key=True)
    command = db.Column(db.String(100), unique=True, nullable=False)
    is_blocked = db.Column(db.Boolean, default=True)
    description = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "command": self.command, "is_blocked": self.is_blocked,
            "description": self.description,
        }


class AuthConfig(db.Model):
    """SOURCE database table/field mappings for authentication configuration."""
    __tablename__ = "auth_config"
    
    id = db.Column(db.Integer, primary_key=True)
    # Users table
    users_table = db.Column(db.String(255))
    username_field = db.Column(db.String(255))
    password_field = db.Column(db.String(255))
    is_active_field = db.Column(db.String(255))
    is_active_value = db.Column(db.String(255))  # Specific value meaning "active"
    password_hash_type = db.Column(db.String(50), default='bcrypt')  # bcrypt, argon2, plaintext
    
    # Company table
    company_table = db.Column(db.String(255))
    company_id_field = db.Column(db.String(255))
    company_name_field = db.Column(db.String(255))
    company_type_field = db.Column(db.String(255))  # Field for company type (e.g., PARENT_BRANCH, BRANCH)
    user_company_fk_field = db.Column(db.String(255))  # Direct FK in users table
    
    # Many-to-many user-company junction table
    user_companies_junction_table = db.Column(db.String(255))
    user_companies_user_fk = db.Column(db.String(255))
    user_companies_company_fk = db.Column(db.String(255))
    
    # Roles table
    roles_table = db.Column(db.String(255))
    role_id_field = db.Column(db.String(255))
    role_name_field = db.Column(db.String(255))
    
    # Many-to-many user-role junction table
    user_roles_junction_table = db.Column(db.String(255))
    user_roles_user_fk = db.Column(db.String(255))
    user_roles_role_fk = db.Column(db.String(255))
    
    # Metadata
    banned_keywords = db.Column(db.Text)
    configured = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'users_table': self.users_table,
            'username_field': self.username_field,
            'password_field': self.password_field,
            'is_active_field': self.is_active_field,
            'is_active_value': self.is_active_value,
            'password_hash_type': self.password_hash_type,
            'company_table': self.company_table,
            'company_id_field': self.company_id_field,
            'company_name_field': self.company_name_field,
            'company_type_field': self.company_type_field,
            'user_company_fk_field': self.user_company_fk_field,
            'user_companies_junction_table': self.user_companies_junction_table,
            'user_companies_user_fk': self.user_companies_user_fk,
            'user_companies_company_fk': self.user_companies_company_fk,
            'roles_table': self.roles_table,
            'role_id_field': self.role_id_field,
            'role_name_field': self.role_name_field,
            'user_roles_junction_table': self.user_roles_junction_table,
            'user_roles_user_fk': self.user_roles_user_fk,
            'user_roles_role_fk': self.user_roles_role_fk,
            'banned_keywords': self.banned_keywords,
            'configured': self.configured,
        }


class SecuritySetting(db.Model):
    """Security configuration for password/keyword restrictions."""
    __tablename__ = "security_settings"
    
    id = db.Column(db.Integer, primary_key=True)
    sql_banned_keywords = db.Column(db.Text, default='password,secret,api_key,token,DELETE,DROP,ALTER')
    require_password_in_results = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'sql_banned_keywords': self.sql_banned_keywords,
            'require_password_in_results': self.require_password_in_results,
        }


class Setting(db.Model):
    """Generic key/value settings store (one row per settings key)."""
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(120), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)  # JSON-encoded
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_value(self):
        try:
            return json.loads(self.value) if self.value else None
        except (json.JSONDecodeError, TypeError):
            return self.value

    @staticmethod
    def get(key, default=None):
        row = Setting.query.filter_by(key=key).first()
        return row.get_value() if row else default

    @staticmethod
    def set(key, value):
        row = Setting.query.filter_by(key=key).first()
        encoded = json.dumps(value)
        if row:
            row.value = encoded
            row.updated_at = datetime.utcnow()
        else:
            row = Setting(key=key, value=encoded)
            db.session.add(row)
        db.session.commit()
        return row

    def to_dict(self):
        return {"key": self.key, "value": self.get_value(), "updated_at": self.updated_at.isoformat()}


class AIContext(db.Model):
    """AI System Instructions and Context for LLM responses."""
    __tablename__ = "ai_context"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, default="default")
    is_active = db.Column(db.Boolean, default=True)
    system_instructions = db.Column(db.Text, nullable=False)  # Main system prompt
    response_rules = db.Column(db.Text, nullable=True)  # Additional response formatting rules
    business_rules = db.Column(db.Text, nullable=True)  # Business logic constraints
    data_isolation_rules = db.Column(db.Text, nullable=True)  # Multi-tenant data filtering rules
    vocabulary = db.Column(db.Text, nullable=True)  # Terminology definitions
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # Which admin last edited

    updater = db.relationship("User", foreign_keys=[updated_by])

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "is_active": self.is_active,
            "system_instructions": self.system_instructions,
            "response_rules": self.response_rules,
            "business_rules": self.business_rules,
            "data_isolation_rules": self.data_isolation_rules,
            "vocabulary": self.vocabulary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by,
        }

    @staticmethod
    def get_active():
        """Get the currently active AI context."""
        return AIContext.query.filter_by(is_active=True).first()


class Conversation(db.Model):
    """Multi-turn conversation persisted server-side (SQLite is source of truth)."""
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.String(120), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)  # Owner of conversation
    is_shared = db.Column(db.Boolean, default=False)  # True if conversation is public/shared
    title = db.Column(db.String(300), nullable=False, default="New conversation")
    messages = db.Column(db.Text, nullable=False, default="[]")  # JSON list of turns
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", foreign_keys=[user_id])

    def get_messages(self):
        try:
            return json.loads(self.messages) if self.messages else []
        except (json.JSONDecodeError, TypeError):
            return []

    def to_dict(self, include_messages=True):
        return {
            "id": self.conversation_id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "is_shared": self.is_shared,
            "title": self.title,
            "messages": self.get_messages() if include_messages else [],
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class AuditLog(db.Model):
    """Query audit trail (prompt, rewritten prompt, generated SQL, status, user, role)."""
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.String(120), index=True)
    user_id = db.Column(db.Integer, nullable=True, index=True)  # User who made the request
    username = db.Column(db.String(255), nullable=True, index=True)  # Username for easy reference
    role_name = db.Column(db.String(255), nullable=True)  # Role(s) of the user (comma-separated if multiple)
    user_query = db.Column(db.Text)
    rewritten_query = db.Column(db.Text)
    generated_sql = db.Column(db.Text)
    row_count = db.Column(db.Integer, default=0)
    llm_provider = db.Column(db.String(50))
    llm_model = db.Column(db.String(100))
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    duration_ms = db.Column(db.Integer, default=0)
    is_api = db.Column(db.Boolean, default=False, index=True)  # True if request came from API/Postman
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "username": self.username,
            "role_name": self.role_name,
            "user_query": self.user_query,
            "rewritten_query": self.rewritten_query,
            "generated_sql": self.generated_sql,
            "row_count": self.row_count,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "success": self.success,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "is_api": self.is_api,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AuditLogDetail(db.Model):
    """Extended per-audit details for observability and debugging."""
    __tablename__ = "audit_log_details"

    id = db.Column(db.Integer, primary_key=True)
    audit_log_id = db.Column(db.Integer, db.ForeignKey("audit_logs.id"), unique=True, nullable=False, index=True)
    response_text = db.Column(db.Text)
    context_cache = db.Column(db.Text)  # JSON string
    token_usage = db.Column(db.Text)    # JSON string
    token_input = db.Column(db.Integer, default=0)
    token_output = db.Column(db.Integer, default=0)
    cache_creation_tokens = db.Column(db.Integer, default=0)
    cache_read_tokens = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        def _loads(raw, default):
            if not raw:
                return default
            try:
                return json.loads(raw)
            except Exception:
                return default

        return {
            "id": self.id,
            "audit_log_id": self.audit_log_id,
            "response_text": self.response_text,
            "context_cache": _loads(self.context_cache, {}),
            "token_usage": _loads(self.token_usage, {}),
            "token_input": self.token_input or 0,
            "token_output": self.token_output or 0,
            "cache_creation_tokens": self.cache_creation_tokens or 0,
            "cache_read_tokens": self.cache_read_tokens or 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TrainingItem(db.Model):
    """Metadata mirror of Vanna training data (DDL / documentation / question-SQL)."""
    __tablename__ = "training_items"

    id = db.Column(db.Integer, primary_key=True)
    item_type = db.Column(db.String(20), nullable=False)  # ddl | documentation | sql
    rule = db.Column(db.String(20), default="optional")  # optional | compulsory
    access = db.Column(db.String(20), default="all")  # all | authenticated
    source_kind = db.Column(db.String(40), default="manual")  # manual | knowledge_base
    source_name = db.Column(db.String(255))
    source_file_type = db.Column(db.String(40))
    question = db.Column(db.Text)        # for sql pairs
    content = db.Column(db.Text, nullable=False)  # ddl text / doc text / sql text
    vanna_id = db.Column(db.String(200))  # id returned by Vanna train()
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "item_type": self.item_type,
            "rule": self.rule or "optional",
            "access": self.access or "all",
            "source_kind": self.source_kind or "manual",
            "source_name": self.source_name,
            "source_file_type": self.source_file_type,
            "question": self.question,
            "content": self.content,
            "vanna_id": self.vanna_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserSettings(db.Model):
    """Per-user application settings (audio, auto-speak, etc.)."""
    __tablename__ = "user_settings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False, index=True)
    audio_settings = db.Column(db.Text)  # JSON: {voiceGender, pitch, rate, volume}
    auto_speak = db.Column(db.Boolean, default=False)  # Auto-speak chat responses

    def get_audio_settings(self):
        """Parse audio settings JSON."""
        if self.audio_settings:
            try:
                return json.loads(self.audio_settings)
            except:
                return {}
        return {}

    def set_audio_settings(self, settings: dict):
        """Store audio settings as JSON."""
        self.audio_settings = json.dumps(settings)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "audio_settings": self.get_audio_settings(),
            "auto_speak": self.auto_speak,
        }


class StoredEmail(db.Model):
    """Downloaded and stored emails from configured email account."""
    __tablename__ = "stored_emails"

    id = db.Column(db.Integer, primary_key=True)
    email_uid = db.Column(db.String(255), unique=True, nullable=False, index=True)  # IMAP UID
    from_address = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text)  # Plain text body
    html_body = db.Column(db.Text)  # HTML body
    received_date = db.Column(db.DateTime, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    folder = db.Column(db.String(100), default='INBOX')  # Email folder name
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "email_uid": self.email_uid,
            "from_address": self.from_address,
            "subject": self.subject,
            "body": self.body,
            "html_body": self.html_body,
            "received_date": self.received_date.isoformat() if self.received_date else None,
            "is_read": self.is_read,
            "folder": self.folder,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DraftEmail(db.Model):
    """Draft/outbox emails: composed but not yet sent."""
    __tablename__ = "draft_emails"

    id = db.Column(db.Integer, primary_key=True)
    to_address = db.Column(db.String(255), nullable=False)
    cc_address = db.Column(db.String(500), nullable=True)  # Comma-separated CC recipients
    bcc_address = db.Column(db.String(500), nullable=True)  # Comma-separated BCC recipients
    subject = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text)
    html_body = db.Column(db.Text)
    status = db.Column(db.String(50), default='draft')  # draft, pending_review, sent, failed
    in_reply_to = db.Column(db.Integer, db.ForeignKey("stored_emails.id"), nullable=True)  # If replying to an email
    auto_generated = db.Column(db.Boolean, default=False)  # Was this generated by AI auto-reply?
    ai_prompt = db.Column(db.Text, nullable=True)  # The prompt used to generate this email
    error_message = db.Column(db.Text, nullable=True)  # Error if sending failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "to_address": self.to_address,
            "cc_address": self.cc_address,
            "bcc_address": self.bcc_address,
            "subject": self.subject,
            "body": self.body,
            "html_body": self.html_body,
            "status": self.status,
            "in_reply_to": self.in_reply_to,
            "auto_generated": self.auto_generated,
            "ai_prompt": self.ai_prompt,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }


class AutoReplySettings(db.Model):
    """Auto-reply configuration for email."""
    __tablename__ = "auto_reply_settings"

    id = db.Column(db.Integer, primary_key=True)
    enabled = db.Column(db.Boolean, default=False)
    mode = db.Column(db.String(50), default='review')  # 'auto' (send immediately) or 'review' (save to drafts)
    ai_instructions = db.Column(db.Text)  # Custom instructions for AI to generate replies
    use_database = db.Column(db.Boolean, default=True)  # Whether to fetch data from database
    database_context = db.Column(db.Text)  # JSON: which tables/fields to use for context
    reply_template = db.Column(db.Text)  # Optional template for replies
    enabled_folders = db.Column(db.String(500))  # Comma-separated list of folders to auto-reply to
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "enabled": self.enabled,
            "mode": self.mode,
            "ai_instructions": self.ai_instructions,
            "use_database": self.use_database,
            "database_context": json.loads(self.database_context) if self.database_context else {},
            "reply_template": self.reply_template,
            "enabled_folders": self.enabled_folders.split(',') if self.enabled_folders else ['INBOX'],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SentEmail(db.Model):
    """Track emails sent by the app (from AI replies or manual sends)."""
    __tablename__ = "sent_emails"

    id = db.Column(db.Integer, primary_key=True)
    to_address = db.Column(db.String(255), nullable=False)
    cc_address = db.Column(db.String(500), nullable=True)  # Comma-separated CC recipients
    bcc_address = db.Column(db.String(500), nullable=True)  # Comma-separated BCC recipients
    subject = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text)
    html_body = db.Column(db.Text)
    in_reply_to = db.Column(db.Integer, db.ForeignKey("stored_emails.id"), nullable=True)  # If replying to received email
    from_draft = db.Column(db.Integer, db.ForeignKey("draft_emails.id"), nullable=True)  # Associated draft
    ai_generated = db.Column(db.Boolean, default=False)  # Was this generated by AI?
    ai_context = db.Column(db.Text)  # JSON: context data used for generating reply
    status = db.Column(db.String(50), default='sent')  # sent, failed, pending
    error_message = db.Column(db.Text, nullable=True)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "to_address": self.to_address,
            "cc_address": self.cc_address,
            "bcc_address": self.bcc_address,
            "subject": self.subject,
            "body": self.body,
            "html_body": self.html_body,
            "in_reply_to": self.in_reply_to,
            "from_draft": self.from_draft,
            "ai_generated": self.ai_generated,
            "ai_context": json.loads(self.ai_context) if self.ai_context else {},
            "status": self.status,
            "error_message": self.error_message,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class VoiceTraining(db.Model):
    """Store user voice training samples for speaker identification in multi-person conversations."""
    __tablename__ = "voice_training"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    voice_sample = db.Column(db.LargeBinary)  # Stores the audio data
    sample_text = db.Column(db.String(255))  # Text that was spoken in the sample
    sample_duration = db.Column(db.Float)  # Duration in seconds
    voice_encoding = db.Column(db.Text)  # JSON: voice characteristics (pitch, formants, etc.)
    training_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "sample_text": self.sample_text,
            "sample_duration": self.sample_duration,
            "training_date": self.training_date.isoformat() if self.training_date else None,
        }


class TableRoleAccess(db.Model):
    """Table-level access control: which roles have access to which tables in the source database."""
    __tablename__ = "table_role_access"

    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(255), nullable=False, index=True)  # Name from source database
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("table_name", "role_id", name="uq_table_role"),)

    role = db.relationship("Role", foreign_keys=[role_id])

    def to_dict(self):
        return {
            "id": self.id,
            "table_name": self.table_name,
            "role_id": self.role_id,
            "role_name": self.role.name if self.role else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class LastEmailSync(db.Model):
    """Track sync progress to prevent duplicate email downloads."""
    __tablename__ = "last_email_sync"

    id = db.Column(db.Integer, primary_key=True)
    folder = db.Column(db.String(255), unique=True, nullable=False, index=True)  # e.g., 'INBOX', 'INBOX.Sent'
    last_sync_uid = db.Column(db.String(255), nullable=True)  # Last email UID synced from this folder
    last_sync_date = db.Column(db.DateTime, nullable=True)  # Date of last sync
    total_synced = db.Column(db.Integer, default=0)  # Total emails synced for this folder
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "folder": self.folder,
            "last_sync_uid": self.last_sync_uid,
            "last_sync_date": self.last_sync_date.isoformat() if self.last_sync_date else None,
            "total_synced": self.total_synced,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SocialMediaAccount(db.Model):
    """Social media account configuration (WhatsApp, etc.) for multi-channel support."""
    __tablename__ = "social_media_accounts"

    id = db.Column(db.Integer, primary_key=True)
    channel_type = db.Column(db.String(50), nullable=False, index=True)  # 'whatsapp', 'telegram', etc.
    account_id = db.Column(db.String(255), nullable=False)  # Phone number for WhatsApp, username for others
    account_name = db.Column(db.String(255))  # Display name
    api_key = db.Column(db.Text)  # API key or auth token (encrypted in production)
    auth_data = db.Column(db.Text)  # JSON: additional auth data
    enabled = db.Column(db.Boolean, default=True)
    treat_as_prompt = db.Column(db.Boolean, default=True)  # Process incoming messages as prompts
    use_context = db.Column(db.Boolean, default=True)  # Use training data context in responses
    use_security_policies = db.Column(db.Boolean, default=True)  # Apply security policies
    owner_number = db.Column(db.String(255))  # For WhatsApp: only respond to this number
    auto_response_enabled = db.Column(db.Boolean, default=False)  # Auto-response mode
    response_template = db.Column(db.Text)  # Optional: response template
    ai_instructions = db.Column(db.Text)  # Custom AI instructions for this channel
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "channel_type": self.channel_type,
            "account_id": self.account_id,
            "account_name": self.account_name,
            "enabled": self.enabled,
            "treat_as_prompt": self.treat_as_prompt,
            "use_context": self.use_context,
            "use_security_policies": self.use_security_policies,
            "owner_number": self.owner_number,
            "auto_response_enabled": self.auto_response_enabled,
            "response_template": self.response_template,
            "ai_instructions": self.ai_instructions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SocialMediaMessage(db.Model):
    """Incoming messages from social media channels."""
    __tablename__ = "social_media_messages"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("social_media_accounts.id"), nullable=False, index=True)
    channel_type = db.Column(db.String(50), nullable=False)  # 'whatsapp', 'telegram', etc.
    sender_id = db.Column(db.String(255), nullable=False)  # Phone/username/user ID
    sender_name = db.Column(db.String(255))
    message_text = db.Column(db.Text, nullable=False)
    message_id = db.Column(db.String(255), unique=True, index=True)  # Unique message ID from provider
    received_at = db.Column(db.DateTime, nullable=False, index=True)
    is_processed = db.Column(db.Boolean, default=False)  # Whether AI response was generated
    is_owner_message = db.Column(db.Boolean, default=False)  # Is this from the account owner
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    account = db.relationship("SocialMediaAccount", foreign_keys=[account_id])

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "channel_type": self.channel_type,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "message_text": self.message_text,
            "message_id": self.message_id,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "is_processed": self.is_processed,
            "is_owner_message": self.is_owner_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SocialMediaResponse(db.Model):
    """Responses sent via social media channels."""
    __tablename__ = "social_media_responses"

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey("social_media_messages.id"), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey("social_media_accounts.id"), nullable=False, index=True)
    response_text = db.Column(db.Text, nullable=False)
    ai_generated = db.Column(db.Boolean, default=True)  # Generated by AI vs manual
    sent_successfully = db.Column(db.Boolean, default=False)
    external_message_id = db.Column(db.String(255))  # Message ID from provider after sending
    prompt_used = db.Column(db.Text)  # The prompt sent to LLM
    context_used = db.Column(db.Text)  # JSON: context data used (training, security, etc.)
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    message = db.relationship("SocialMediaMessage", foreign_keys=[message_id])
    account = db.relationship("SocialMediaAccount", foreign_keys=[account_id])

    def to_dict(self):
        return {
            "id": self.id,
            "message_id": self.message_id,
            "account_id": self.account_id,
            "response_text": self.response_text,
            "ai_generated": self.ai_generated,
            "sent_successfully": self.sent_successfully,
            "external_message_id": self.external_message_id,
            "prompt_used": self.prompt_used,
            "context_used": self.context_used,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

