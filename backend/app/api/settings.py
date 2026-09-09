"""Settings API: LLM, Database, Vector store config + engine status."""
import logging
import os
import re
from pathlib import Path
import sqlite3
from sqlalchemy.engine import make_url

from flask import Blueprint, request, jsonify, has_app_context, current_app

from ..config import Config
from ..models import Setting
from ..extensions import db
from ..llm import get_llm_settings, build_llm
from ..bootstrap import get_vector_settings, get_db_settings, reinitialize_vanna
from ..vanna_service import get_vanna_service
from ..microservice_auth import extract_user_from_token, MICROSERVICE_MODE
from ..auth import require_auth
from ..db_migration import (
    parse_db_url, build_db_url, test_connection, create_database_if_not_exists,
    migrate_admin_db, get_db_info, validate_db_url, _update_env_file
)

logger = logging.getLogger(__name__)
settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")

# Keys masked in responses (never echo secrets back to the client).
_SECRET_KEYS = {"gemini_api_key", "openai_api_key", "anthropic_api_key", "pinecone_api_key"}


def _docs_dir() -> Path:
    """Resolve docs directory with multiple fallback strategies."""
    # Strategy 1: Check environment variable (DOCS_FOLDER - set by DevOps/Docker)
    env_docs = os.getenv("DOCS_FOLDER")
    if env_docs:
        docs_path = Path(env_docs)
        if docs_path.exists() and docs_path.is_dir():
            return docs_path
    
    # Strategy 2: Relative to this file (backend/app/api/settings.py -> backend -> project_root)
    settings_file = Path(__file__).resolve()
    backend_root = settings_file.parents[2]
    docs_candidate = (backend_root.parent / "docs").resolve()
    
    if docs_candidate.exists() and docs_candidate.is_dir():
        return docs_candidate
    
    # Strategy 3: Check if docs is relative to current working directory
    cwd_docs = Path.cwd() / "docs"
    if cwd_docs.exists() and cwd_docs.is_dir():
        return cwd_docs.resolve()
    
    # Strategy 4: Check parent of current working directory
    parent_docs = Path.cwd().parent / "docs"
    if parent_docs.exists() and parent_docs.is_dir():
        return parent_docs.resolve()
    
    # Default to environment variable or calculated path
    return Path(env_docs) if env_docs else docs_candidate


def _doc_title_from_name(name: str) -> str:
    base = name.replace(".md", "").replace("_", " ").replace("-", " ")
    return " ".join(part.capitalize() for part in base.split())


def _sanitize_doc_text(content: str) -> str:
    """Hide provider-specific wording in surfaced documentation."""
    if not content:
        return ""
    sanitized = re.sub(r"\bVanna's\b", "LLM's", content, flags=re.IGNORECASE)
    sanitized = re.sub(r"\bVanna LLM\b", "LLM", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"\bVanna\b", "LLM", sanitized, flags=re.IGNORECASE)
    return sanitized


def _resolve_sqlite_path(url: str) -> str:
    """Resolve sqlite URL to a stable absolute file path.

    Uses SQLAlchemy URL parsing and anchors relative DB files to backend root,
    not the current process working directory.
    """
    if not url or not url.startswith("sqlite"):
        return ""
    try:
        parsed = make_url(url)
        db_path = parsed.database or ""
    except Exception:
        db_path = ""

    if not db_path:
        return ""

    # Windows absolute path may come as /C:/... from URL parser.
    if os.name == "nt" and len(db_path) >= 3 and db_path[0] == "/" and db_path[2] == ":":
        db_path = db_path[1:]

    path_obj = Path(db_path)
    if not path_obj.is_absolute():
        # Flask/SQLAlchemy treats relative sqlite paths as instance-relative.
        if has_app_context():
            base_dir = Path(current_app.instance_path)
        else:
            backend_dir = Path(__file__).resolve().parents[2]
            base_dir = backend_dir / "instance"
        path_obj = (base_dir / path_obj).resolve()

    return str(path_obj)


def _mask(d: dict) -> dict:
    out = dict(d)
    for k in _SECRET_KEYS:
        if out.get(k):
            out[k] = "••••••••"
            out[f"{k}_set"] = True
        else:
            out[f"{k}_set"] = False
    return out


def _merge_secrets(existing: dict, incoming: dict) -> dict:
    """Keep stored secret if the client sent a masked/blank placeholder."""
    merged = dict(existing or {})
    for k, v in (incoming or {}).items():
        if k in _SECRET_KEYS and (not v or v == "••••••••"):
            continue  # don't overwrite stored secret with mask/blank
        merged[k] = v
    return merged


# ----------------------------- LLM ----------------------------- #
@settings_bp.route("/llm", methods=["GET"])
def get_llm():
    return jsonify({"success": True, "config": _mask(get_llm_settings())}), 200


@settings_bp.route("/llm", methods=["POST"])
def set_llm():
    incoming = request.get_json(silent=True) or {}
    current = Setting.get("llm_config") or {}
    Setting.set("llm_config", _merge_secrets(current, incoming))
    status = reinitialize_vanna()
    return jsonify({"success": True, "config": _mask(get_llm_settings()), "engine": status}), 200


@settings_bp.route("/llm/providers", methods=["GET"])
def list_providers():
    return jsonify({
        "success": True,
        "providers": [
            {"id": "gemini", "label": "Google Gemini", "models": ["gemini-2.0-flash", "gemini-1.5-pro"]},
            {"id": "openai", "label": "OpenAI", "models": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"]},
            {"id": "anthropic", "label": "Anthropic Claude", "models": ["claude-sonnet-4-6", "claude-3-5-sonnet-20241022"]},
            {"id": "huggingface", "label": "Hugging Face (offline, free)", "models": ["google/flan-t5-base", "google/flan-t5-large"]},
        ],
    }), 200


# --------------------------- Database --------------------------- #
@settings_bp.route("/database", methods=["GET"])
def get_db():
    return jsonify({"success": True, "config": get_db_settings()}), 200


@settings_bp.route("/database", methods=["POST"])
def set_db():
    incoming = request.get_json(silent=True) or {}
    Setting.set("db_config", {"source_db_url": incoming.get("source_db_url", "")})
    status = reinitialize_vanna()
    return jsonify({"success": True, "config": get_db_settings(), "engine": status}), 200


@settings_bp.route("/database/test", methods=["POST"])
def test_db():
    """Test connection to SOURCE database."""
    incoming = request.get_json(silent=True) or {}
    url = incoming.get("source_db_url") or get_db_settings()["source_db_url"]
    if not url:
        return jsonify({
            "success": False, 
            "error": "No database URL provided.",
            "guidance": "Set SOURCE_DB_URL environment variable or provide source_db_url in request body"
        }), 400
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return jsonify({"success": True, "message": "Connection OK."}), 200
    except Exception as exc:  # noqa: BLE001
        return jsonify({
            "success": False, 
            "error": str(exc),
            "guidance": "Verify SOURCE_DB_URL credentials, hostname, port, and that database is accessible"
        }), 400


# ---------------------- Admin Database Migration ---------------------- #
@settings_bp.route("/admin-db/info", methods=["GET"])
def get_admin_db_info():
    """Get information about current admin database."""
    info = get_db_info(Config.ADMIN_DB_URL)
    return jsonify({"success": True, "admin_db": info}), 200


@settings_bp.route("/admin-db/update-url", methods=["POST"])
def update_admin_db_url():
    """Update the admin database URL."""
    incoming = request.get_json(silent=True) or {}
    new_url = incoming.get("admin_db_url", "").strip()
    
    if not new_url:
        return jsonify({"success": False, "error": "Admin DB URL cannot be empty"}), 400
    
    # Test connection to new database
    success, msg = test_connection(new_url)
    if not success:
        return jsonify({"success": False, "error": f"Connection test failed: {msg}"}), 400
    
    # Update .env file
    if not _update_env_file("ADMIN_DB_URL", new_url):
        return jsonify({"success": False, "error": "Failed to update .env file"}), 500
    
    return jsonify({
        "success": True, 
        "message": "Admin database URL updated. Please restart the application to use the new database.",
        "admin_db": get_db_info(new_url)
    }), 200


@settings_bp.route("/database/info", methods=["GET"])
def get_source_db_info():
    """Get information about current source database."""
    db_settings = get_db_settings()
    source_db_url = db_settings.get("source_db_url") or Config.SOURCE_DB_URL
    if not source_db_url:
        return jsonify({"success": False, "error": "No source database configured"}), 400
    try:
        info = get_db_info(source_db_url)
        return jsonify({"success": True, "source_db": info}), 200
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Error getting source DB info: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 400


@settings_bp.route("/admin-db/migrate", methods=["POST"])
def migrate_admin_database():
    """Migrate admin database to a different type (PostgreSQL, MySQL, SQLite)."""
    incoming = request.get_json(silent=True) or {}
    db_type = incoming.get("db_type", "").lower()
    
    # Get connection parameters
    if db_type == "sqlite":
        path = incoming.get("path", "assistantai.db").strip()
        if not path:
            return jsonify({"success": False, "error": "SQLite path is required"}), 400
        target_url = f"sqlite:///{path}"
    elif db_type == "postgresql":
        host = incoming.get("host", "localhost").strip()
        port = incoming.get("port", 5432)
        database = incoming.get("database", "assistantai").strip()
        username = incoming.get("username", "").strip()
        password = incoming.get("password", "").strip()
        
        if not database:
            return jsonify({"success": False, "error": "Database name is required"}), 400
        
        # Validate and build URL
        valid, msg = validate_db_url(db_type, host=host, port=port, database=database, username=username, password=password)
        if not valid:
            return jsonify({"success": False, "error": msg}), 400
        
        target_url = build_db_url(db_type, host=host, port=port, database=database, username=username, password=password)
    elif db_type == "mysql":
        host = incoming.get("host", "localhost").strip()
        port = incoming.get("port", 3306)
        database = incoming.get("database", "assistantai").strip()
        username = incoming.get("username", "").strip()
        password = incoming.get("password", "").strip()
        
        if not database:
            return jsonify({"success": False, "error": "Database name is required"}), 400
        
        # Validate and build URL
        valid, msg = validate_db_url(db_type, host=host, port=port, database=database, username=username, password=password)
        if not valid:
            return jsonify({"success": False, "error": msg}), 400
        
        target_url = build_db_url(db_type, host=host, port=port, database=database, username=username, password=password)
    else:
        return jsonify({"success": False, "error": f"Unsupported database type: {db_type}"}), 400
    
    # Test target connection first
    success, msg = test_connection(target_url)
    if not success:
        return jsonify({"success": False, "error": f"Cannot connect to target database: {msg}"}), 400
    
    # Perform migration
    try:
        success, msg = migrate_admin_db(db_type, target_url)
        if success:
            return jsonify({
                "success": True,
                "message": msg,
                "new_admin_db": get_db_info(target_url),
                "info": "App will use new database on next restart"
            }), 200
        else:
            return jsonify({"success": False, "error": msg}), 500
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Admin DB migration error: {exc}")
        return jsonify({"success": False, "error": f"Migration failed: {str(exc)}"}), 500


@settings_bp.route("/admin-db/create", methods=["POST"])
def create_admin_database():
    """Create a new admin database (useful before migration)."""
    incoming = request.get_json(silent=True) or {}
    db_type = incoming.get("db_type", "").lower()
    
    # Build URL based on type
    if db_type == "sqlite":
        path = incoming.get("path", "assistantai_new.db").strip()
        if not path:
            return jsonify({"success": False, "error": "SQLite path is required"}), 400
        target_url = f"sqlite:///{path}"
    elif db_type == "postgresql":
        host = incoming.get("host", "localhost").strip()
        port = incoming.get("port", 5432)
        database = incoming.get("database", "assistantai").strip()
        username = incoming.get("username", "").strip()
        password = incoming.get("password", "").strip()
        
        if not database:
            return jsonify({"success": False, "error": "Database name is required"}), 400
        
        target_url = build_db_url(db_type, host=host, port=port, database=database, username=username, password=password)
    elif db_type == "mysql":
        host = incoming.get("host", "localhost").strip()
        port = incoming.get("port", 3306)
        database = incoming.get("database", "assistantai").strip()
        username = incoming.get("username", "").strip()
        password = incoming.get("password", "").strip()
        
        if not database:
            return jsonify({"success": False, "error": "Database name is required"}), 400
        
        target_url = build_db_url(db_type, host=host, port=port, database=database, username=username, password=password)
    else:
        return jsonify({"success": False, "error": f"Unsupported database type: {db_type}"}), 400
    
    # Create database
    try:
        success, msg = create_database_if_not_exists(target_url)
        if success:
            # Test connection
            test_success, test_msg = test_connection(target_url)
            if test_success:
                return jsonify({
                    "success": True,
                    "message": msg,
                    "database_info": get_db_info(target_url)
                }), 200
            else:
                return jsonify({"success": False, "error": f"Database created but connection failed: {test_msg}"}), 500
        else:
            return jsonify({"success": False, "error": msg}), 500
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Create database error: {exc}")
        return jsonify({"success": False, "error": f"Failed to create database: {str(exc)}"}), 500


@settings_bp.route("/admin-db/test", methods=["POST"])
def test_admin_db():
    """Test connection to a proposed admin database URL."""
    incoming = request.get_json(silent=True) or {}
    db_type = incoming.get("db_type", "").lower()
    
    # Build URL based on type
    if db_type == "sqlite":
        path = incoming.get("path", "assistantai.db").strip()
        target_url = f"sqlite:///{path}"
    elif db_type == "postgresql":
        host = incoming.get("host", "localhost").strip()
        port = incoming.get("port", 5432)
        database = incoming.get("database", "assistantai").strip()
        username = incoming.get("username", "").strip()
        password = incoming.get("password", "").strip()
        target_url = build_db_url(db_type, host=host, port=port, database=database, username=username, password=password)
    elif db_type == "mysql":
        host = incoming.get("host", "localhost").strip()
        port = incoming.get("port", 3306)
        database = incoming.get("database", "assistantai").strip()
        username = incoming.get("username", "").strip()
        password = incoming.get("password", "").strip()
        target_url = build_db_url(db_type, host=host, port=port, database=database, username=username, password=password)
    else:
        return jsonify({"success": False, "error": f"Unsupported database type: {db_type}"}), 400
    
    # Test connection
    success, msg = test_connection(target_url)
    if success:
        db_info = get_db_info(target_url)
        return jsonify({"success": True, "message": msg, "database_info": db_info}), 200
    else:
        return jsonify({"success": False, "error": msg}), 400


@settings_bp.route("/sqlite", methods=["GET"])
def get_sqlite_admin():
    """Expose admin SQLite DB info (read-only)."""
    url = Config.ADMIN_DB_URL or ""
    file_path = _resolve_sqlite_path(url)
    exists = False
    size_bytes = None
    if file_path and os.path.exists(file_path):
        exists = True
        try:
            size_bytes = os.path.getsize(file_path)
        except OSError:
            size_bytes = None
    return jsonify({
        "success": True,
        "admin_db_url": url,
        "file_path": file_path,
        "exists": exists,
        "size_bytes": size_bytes,
    }), 200


def _sqlite_file_path() -> str:
    return _resolve_sqlite_path(Config.ADMIN_DB_URL or "")


def _list_tables(conn):
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    return [r[0] for r in cur.fetchall()]


def _table_columns(conn, table_name: str):
    cur = conn.execute(f'PRAGMA table_info("{table_name}")')
    rows = cur.fetchall()
    cols = []
    pk_col = None
    for r in rows:
        col = {"cid": r[0], "name": r[1], "type": r[2], "notnull": bool(r[3]), "default": r[4], "pk": bool(r[5])}
        cols.append(col)
        if col["pk"]:
            pk_col = col["name"]
    return cols, pk_col


@settings_bp.route("/sqlite/tables", methods=["GET"])
def sqlite_tables():
    path = _sqlite_file_path()
    if not path or not os.path.exists(path):
        return jsonify({"success": False, "error": "SQLite DB file not found."}), 404
    with sqlite3.connect(path) as conn:
        tables = _list_tables(conn)
        out = []
        for t in tables:
            cols, pk_col = _table_columns(conn, t)
            try:
                c = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            except Exception:
                c = 0
            out.append({"table": t, "row_count": c, "columns": cols, "pk_column": pk_col})
    return jsonify({"success": True, "items": out}), 200


@settings_bp.route("/sqlite/table/<table_name>", methods=["GET"])
def sqlite_table_rows(table_name: str):
    page = max(1, request.args.get("page", 1, type=int))
    page_size = min(200, max(1, request.args.get("page_size", 50, type=int)))
    offset = (page - 1) * page_size
    path = _sqlite_file_path()
    if not path or not os.path.exists(path):
        return jsonify({"success": False, "error": "SQLite DB file not found."}), 404
    with sqlite3.connect(path) as conn:
        tables = _list_tables(conn)
        if table_name not in tables:
            return jsonify({"success": False, "error": "Unknown table."}), 404
        cols, pk_col = _table_columns(conn, table_name)
        id_expr = f'"{pk_col}"' if pk_col else 'rowid'
        total = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
        cur = conn.execute(
            f'SELECT {id_expr} AS __record_id, * FROM "{table_name}" LIMIT ? OFFSET ?',
            (page_size, offset),
        )
        names = [d[0] for d in cur.description]
        rows = [dict(zip(names, r)) for r in cur.fetchall()]
    return jsonify({
        "success": True,
        "table": table_name,
        "page": page,
        "page_size": page_size,
        "total": total,
        "columns": cols,
        "pk_column": pk_col,
        "rows": rows,
    }), 200


@settings_bp.route("/sqlite/table/<table_name>", methods=["POST"])
def sqlite_table_insert(table_name: str):
    payload = request.get_json(silent=True) or {}
    row = payload.get("row") or {}
    if not isinstance(row, dict) or not row:
        return jsonify({"success": False, "error": "Body must include non-empty 'row' object."}), 400
    path = _sqlite_file_path()
    if not path or not os.path.exists(path):
        return jsonify({"success": False, "error": "SQLite DB file not found."}), 404
    with sqlite3.connect(path) as conn:
        tables = _list_tables(conn)
        if table_name not in tables:
            return jsonify({"success": False, "error": "Unknown table."}), 404
        cols, _ = _table_columns(conn, table_name)
        allowed = {c["name"] for c in cols}
        keys = [k for k in row.keys() if k in allowed]
        if not keys:
            return jsonify({"success": False, "error": "No valid columns provided."}), 400
        placeholders = ", ".join(["?"] * len(keys))
        col_sql = ", ".join([f'"{k}"' for k in keys])
        values = [row[k] for k in keys]
        conn.execute(f'INSERT INTO "{table_name}" ({col_sql}) VALUES ({placeholders})', values)
        conn.commit()
    return jsonify({"success": True}), 201


@settings_bp.route("/sqlite/table/<table_name>/<record_id>", methods=["PUT", "PATCH"])
def sqlite_table_update(table_name: str, record_id: str):
    payload = request.get_json(silent=True) or {}
    row = payload.get("row") or {}
    if not isinstance(row, dict) or not row:
        return jsonify({"success": False, "error": "Body must include non-empty 'row' object."}), 400
    path = _sqlite_file_path()
    if not path or not os.path.exists(path):
        return jsonify({"success": False, "error": "SQLite DB file not found."}), 404
    with sqlite3.connect(path) as conn:
        tables = _list_tables(conn)
        if table_name not in tables:
            return jsonify({"success": False, "error": "Unknown table."}), 404
        cols, pk_col = _table_columns(conn, table_name)
        allowed = {c["name"] for c in cols}
        keys = [k for k in row.keys() if k in allowed]
        if not keys:
            return jsonify({"success": False, "error": "No valid columns provided."}), 400
        set_sql = ", ".join([f'"{k}"=?' for k in keys])
        values = [row[k] for k in keys]
        id_col = pk_col or "rowid"
        values.append(record_id)
        cur = conn.execute(f'UPDATE "{table_name}" SET {set_sql} WHERE "{id_col}"=?', values)
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"success": False, "error": "Record not found."}), 404
    return jsonify({"success": True}), 200


@settings_bp.route("/sqlite/table/<table_name>/<record_id>", methods=["DELETE"])
def sqlite_table_delete(table_name: str, record_id: str):
    path = _sqlite_file_path()
    if not path or not os.path.exists(path):
        return jsonify({"success": False, "error": "SQLite DB file not found."}), 404
    with sqlite3.connect(path) as conn:
        tables = _list_tables(conn)
        if table_name not in tables:
            return jsonify({"success": False, "error": "Unknown table."}), 404
        _, pk_col = _table_columns(conn, table_name)
        id_col = pk_col or "rowid"
        cur = conn.execute(f'DELETE FROM "{table_name}" WHERE "{id_col}"=?', (record_id,))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"success": False, "error": "Record not found."}), 404
    return jsonify({"success": True}), 200


# -------------------------- Vector store ------------------------ #
@settings_bp.route("/vector", methods=["GET"])
def get_vector():
    return jsonify({"success": True, "config": _mask(get_vector_settings())}), 200


@settings_bp.route("/vector", methods=["POST"])
def set_vector():
    incoming = request.get_json(silent=True) or {}
    current = Setting.get("vector_config") or {}
    Setting.set("vector_config", _merge_secrets(current, incoming))
    status = reinitialize_vanna()
    return jsonify({"success": True, "config": _mask(get_vector_settings()), "engine": status}), 200


@settings_bp.route("/vector/stores", methods=["GET"])
def list_stores():
    return jsonify({
        "success": True,
        "stores": [
            {"id": "chromadb", "label": "ChromaDB (local, free)"},
            {"id": "faiss", "label": "FAISS (local)"},
            {"id": "pinecone", "label": "Pinecone (cloud)"},
        ],
    }), 200


# ---------------------- User Settings ----------------------- #
@settings_bp.route("/user", methods=["GET"])
@require_auth
def get_user_settings():
    """Get current user's settings (audio, auto-speak, etc.)."""
    from ..models import UserSettings
    from ..auth import current_user_context
    
    user_ctx = current_user_context()
    user_id = user_ctx.get('user_id')
    if not user_id:
        return jsonify({
            "success": True,
            "settings": {
                "id": None,
                "user_id": None,
                "audio_settings": {
                    "voiceGender": "female",
                    "pitch": 1,
                    "rate": 1,
                    "volume": 1,
                },
                "auto_speak": False,
                "updated_at": None,
            }
        }), 200
    
    settings = UserSettings.query.filter_by(user_id=user_id).first()
    if not settings:
        return jsonify({
            "success": True,
            "settings": {
                "id": None,
                "user_id": user_id,
                "audio_settings": {
                    "voiceGender": "female",
                    "pitch": 1,
                    "rate": 1,
                    "volume": 1,
                },
                "auto_speak": False,
                "updated_at": None,
            }
        }), 200
    
    return jsonify({"success": True, "settings": settings.to_dict()}), 200


@settings_bp.route("/user", methods=["POST", "PUT"])
@require_auth
def update_user_settings():
    """Update current user's settings."""
    from sqlalchemy.exc import IntegrityError
    from ..models import UserSettings
    from ..auth import current_user_context
    import json
    
    user_ctx = current_user_context()
    user_id = user_ctx.get('user_id')
    if not user_id:
        return jsonify({"success": False, "error": "Not authenticated"}), 401
    
    data = request.get_json(silent=True) or {}
    
    settings = UserSettings.query.filter_by(user_id=user_id).first()
    if not settings:
        settings = UserSettings(user_id=user_id)
        db.session.add(settings)
    
    # Update audio settings
    if "audio_settings" in data and data["audio_settings"]:
        settings.audio_settings = json.dumps(data["audio_settings"])
    
    # Update auto_speak
    if "auto_speak" in data:
        settings.auto_speak = bool(data["auto_speak"])
    
    try:
        db.session.commit()
        return jsonify({"success": True, "settings": settings.to_dict()}), 200
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Failed to save user settings: {e}")
        return jsonify({"success": False, "error": "Failed to save settings"}), 500


# ======================== MICROSERVICE TOKEN VERIFICATION ======================== #
# These endpoints support microservice mode - decrypt and validate JWT tokens

@settings_bp.route("/microservice/status", methods=["GET"])
def microservice_status():
    """Check if microservice mode is enabled and token validation configured."""
    from ..microservice_auth import (
        MICROSERVICE_MODE, MICROSERVICE_TOKEN_ALGORITHM, 
        MICROSERVICE_TOKEN_PUBLIC_KEY, MICROSERVICE_TOKEN_SECRET
    )
    
    return jsonify({
        "success": True,
        "microservice_mode": MICROSERVICE_MODE,
        "token_algorithm": MICROSERVICE_TOKEN_ALGORITHM,
        "has_public_key": bool(MICROSERVICE_TOKEN_PUBLIC_KEY),
        "has_secret": bool(MICROSERVICE_TOKEN_SECRET),
        "message": "Microservice mode is " + ("ENABLED" if MICROSERVICE_MODE else "DISABLED")
    }), 200


@settings_bp.route("/microservice/verify-token", methods=["POST"])
def verify_token():
    """
    Verify and decode a JWT token. 
    
    Accepts:
    - JSON body: {"token": "<token>"} (PREFERRED)
    - Authorization header: "Bearer <token>" (fallback)
    - Form data: token=<token> (fallback)
    
    Returns decoded token claims and user context.
    """
    from ..microservice_auth import extract_token_from_token_string
    
    # Extract token from multiple sources - prioritize body over header
    token = None
    
    # 1. Check JSON body FIRST
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    
    # 2. Check form data
    if not token:
        token = request.form.get("token")
    
    # 3. Check Authorization header (fallback)
    if not token:
        auth_header = request.headers.get("Authorization", "").strip()
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    
    if not token:
        return jsonify({
            "success": False,
            "error": "No token provided. Send as JSON body {\"token\": \"...\"}, form data, or Authorization header."
        }), 400
    
    try:
        user_ctx = extract_user_from_token(token)
        
        if not user_ctx:
            return jsonify({
                "success": False,
                "error": "Token verification failed or token expired",
                "debug_info": "Check token validity and algorithm configuration"
            }), 401
        
        # Extract raw_payload and remove it from user_context for cleaner display
        raw_payload = user_ctx.pop("raw_payload", {})
        
        return jsonify({
            "success": True,
            "raw_claims": raw_payload,
            "user_context": user_ctx,
            "message": f"✅ Token verified for user: {user_ctx.get('email', user_ctx.get('username', 'unknown'))}"
        }), 200
        
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "debug_info": "Check token format and expiration"
        }), 400


@settings_bp.route("/microservice/decode-token", methods=["POST"])
def decode_token_no_verify():
    """
    Decode a JWT token WITHOUT verifying signature (dev/debug only).
    Useful for inspecting token claims during development.
    
    Accepts:
    - JSON body: {"token": "<token>"} (PREFERRED)
    - Form data: token=<token>
    - Authorization header: "Bearer <token>" (fallback)
    
    WARNING: This does NOT validate the token signature!
    """
    import jwt
    
    # Extract token - prioritize body over header
    token = None
    
    # 1. Check JSON body FIRST
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    
    # 2. Check form data
    if not token:
        token = request.form.get("token")
    
    # 3. Check Authorization header (fallback)
    if not token:
        auth_header = request.headers.get("Authorization", "").strip()
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    
    if not token:
        return jsonify({
            "success": False,
            "error": "No token provided. Send as JSON body {\"token\": \"...\"}, form data, or Authorization header."
        }), 400
    
    try:
        # Decode without verification - only for debugging!
        decoded = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
        
        return jsonify({
            "success": True,
            "decoded_claims": decoded,
            "warning": "⚠️  Signature was NOT verified - for debugging only!"
        }), 200
        
    except jwt.DecodeError as e:
        return jsonify({
            "success": False,
            "error": f"Could not decode token: {e}"
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


@settings_bp.route("/microservice/modify-token-expiry", methods=["POST"])
def modify_token_expiry():
    """
    Modify a JWT token's expiry date and re-sign it.
    
    Accepts:
    - JSON body: {"token": "<token>", "hours_adjustment": 24}
    
    hours_adjustment: Number of hours to ADD (positive) or SUBTRACT (negative) from current expiry
    - Example: 24 = extend expiry by 24 hours
    - Example: -12 = shorten expiry by 12 hours
    
    Returns: New token with modified expiry, or error if token cannot be modified
    """
    import jwt
    from datetime import datetime, timedelta, timezone
    from ..microservice_auth import (
        MICROSERVICE_TOKEN_ALGORITHM, 
        MICROSERVICE_TOKEN_PUBLIC_KEY, 
        MICROSERVICE_TOKEN_SECRET
    )
    
    data = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()
    hours_adjustment = data.get("hours_adjustment", 0)
    
    if not token:
        return jsonify({
            "success": False,
            "error": "Token is required"
        }), 400
    
    try:
        hours_adjustment = float(hours_adjustment)
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "hours_adjustment must be a number"
        }), 400
    
    try:
        # Decode without verification to get claims
        decoded = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
        
        # Get current expiry
        current_exp = decoded.get("exp")
        if not current_exp:
            return jsonify({
                "success": False,
                "error": "Token does not have an expiry claim (exp)"
            }), 400
        
        # Calculate new expiry
        current_exp_dt = datetime.fromtimestamp(current_exp, tz=timezone.utc)
        new_exp_dt = current_exp_dt + timedelta(hours=hours_adjustment)
        
        # Prevent expiry in the past
        now = datetime.now(timezone.utc)
        if new_exp_dt < now:
            return jsonify({
                "success": False,
                "error": f"New expiry ({new_exp_dt.isoformat()}) would be in the past. Please use a positive adjustment."
            }), 400
        
        # Modify the exp claim
        decoded["exp"] = int(new_exp_dt.timestamp())
        
        # For token signing, we need the appropriate key based on algorithm
        algorithm = MICROSERVICE_TOKEN_ALGORITHM or "HS256"
        
        if algorithm.startswith("RS") or algorithm.startswith("ES") or algorithm.startswith("PS"):
            # Asymmetric algorithms (RS256, ES256, PS256, etc.) require private key
            # For now, we don't support re-signing with asymmetric keys
            # because we don't have access to the private key (only public key for verification)
            return jsonify({
                "success": False,
                "error": f"Token expiry modification is not supported for {algorithm} algorithm",
                "reason": "Asymmetric signing algorithms require a private key, which is not available in this service",
                "hint": "This feature is designed for symmetric algorithms like HS256"
            }), 501  # 501 Not Implemented
        else:
            # Symmetric algorithms (HS256, etc.) use a shared secret
            signing_key = MICROSERVICE_TOKEN_SECRET
            if not signing_key:
                return jsonify({
                    "success": False,
                    "error": "Token signing credentials not configured on server",
                    "debug_info": "Set MICROSERVICE_TOKEN_SECRET environment variable"
                }), 500
        
        # Re-encode with new expiry
        new_token = jwt.encode(decoded, signing_key, algorithm=algorithm)
        
        logger.info(f"✏️  Modified token expiry: {current_exp_dt.isoformat()} → {new_exp_dt.isoformat()} ({hours_adjustment:+.1f} hours)")
        
        return jsonify({
            "success": True,
            "new_token": new_token,
            "old_expiry": current_exp_dt.isoformat(),
            "new_expiry": new_exp_dt.isoformat(),
            "hours_adjusted": hours_adjustment,
            "message": f"Token expiry modified: {current_exp_dt.strftime('%Y-%m-%d %H:%M:%S')} → {new_exp_dt.strftime('%Y-%m-%d %H:%M:%S')}"
        }), 200
        
    except jwt.DecodeError as e:
        return jsonify({
            "success": False,
            "error": f"Could not decode token: {e}"
        }), 400


# ======================== AI CONTEXT MANAGEMENT ======================== #
@settings_bp.route("/ai-context", methods=["GET"])
@require_auth
def get_ai_context():
    """Get the currently active AI context."""
    from ..models import AIContext
    from ..auth import current_user_context
    
    try:
        ctx = current_user_context() or {}
        if not (ctx.get('is_admin') or ctx.get('is_central_admin')):
            return jsonify({"success": False, "error": "Only admins can access AI context settings"}), 403
        
        # Get active context
        active_context = AIContext.get_active()
        if active_context:
            return jsonify({"success": True, "context": active_context.to_dict()}), 200
        
        # If no active context exists, return default/empty
        return jsonify({
            "success": True, 
            "context": {
                "id": None,
                "name": "default",
                "is_active": True,
                "system_instructions": "",
                "response_rules": "",
                "business_rules": "",
                "data_isolation_rules": "",
                "vocabulary": ""
            }
        }), 200
    except Exception as e:
        logger.error(f"Error getting AI context: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route("/ai-context", methods=["POST"])
@require_auth
def update_ai_context():
    """Create or update AI context."""
    from ..models import AIContext
    from ..auth import current_user_context
    from ..extensions import db
    
    try:
        ctx = current_user_context() or {}
        if not (ctx.get('is_admin') or ctx.get('is_central_admin')):
            return jsonify({"success": False, "error": "Only admins can manage AI context"}), 403
        
        user_id = ctx.get('user_id')
        data = request.get_json(silent=True) or {}
        
        context_id = data.get('id')
        
        if context_id:
            # Update existing context
            ai_context = AIContext.query.get(context_id)
            if not ai_context:
                return jsonify({"success": False, "error": "AI context not found"}), 404
        else:
            # Deactivate all existing contexts and create new one
            AIContext.query.filter_by(is_active=True).update({"is_active": False})
            ai_context = AIContext()
            db.session.add(ai_context)
        
        # Update fields
        ai_context.name = data.get('name', 'default')
        ai_context.is_active = True
        ai_context.system_instructions = data.get('system_instructions', '')
        ai_context.response_rules = data.get('response_rules', '')
        ai_context.business_rules = data.get('business_rules', '')
        ai_context.data_isolation_rules = data.get('data_isolation_rules', '')
        ai_context.vocabulary = data.get('vocabulary', '')
        ai_context.updated_by = user_id
        
        db.session.commit()
        
        logger.info(f"AI context updated by user {user_id}: {ai_context.name}")
        
        return jsonify({
            "success": True,
            "context": ai_context.to_dict(),
            "message": "AI context saved successfully"
        }), 200
    except Exception as e:
        logger.error(f"Error updating AI context: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route("/ai-context/default", methods=["POST"])
@require_auth
def reset_ai_context_to_default():
    """Reset AI context to the built-in default from response_guide.py."""
    from ..models import AIContext
    from ..auth import current_user_context
    from ..response_guide import CLIENTSHOT_SYSTEM_INSTRUCTIONS
    from ..extensions import db
    
    try:
        ctx = current_user_context() or {}
        if not (ctx.get('is_admin') or ctx.get('is_central_admin')):
            return jsonify({"success": False, "error": "Only admins can reset AI context"}), 403
        
        user_id = ctx.get('user_id')
        
        # Deactivate all existing
        AIContext.query.filter_by(is_active=True).update({"is_active": False})
        
        # Create new one with default instructions
        ai_context = AIContext(
            name='default',
            is_active=True,
            system_instructions=CLIENTSHOT_SYSTEM_INSTRUCTIONS,
            response_rules='',
            business_rules='',
            data_isolation_rules='',
            vocabulary='',
            updated_by=user_id
        )
        db.session.add(ai_context)
        db.session.commit()
        
        logger.info(f"AI context reset to default by user {user_id}")
        
        return jsonify({
            "success": True,
            "context": ai_context.to_dict(),
            "message": "AI context reset to default"
        }), 200
    except Exception as e:
        logger.error(f"Error resetting AI context: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    except Exception as e:
        logger.error(f"Error modifying token expiry: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


# ======================== END MICROSERVICE TOKEN VERIFICATION ======================== #


@settings_bp.route("/engine/status", methods=["GET"])
def engine_status():
    return jsonify({"success": True, "status": get_vanna_service().status()}), 200


@settings_bp.route("/engine/reinitialize", methods=["POST"])
def engine_reinit():
    return jsonify({"success": True, "status": reinitialize_vanna()}), 200


@settings_bp.route("/api-doc", methods=["GET"])
def api_doc():
    """Return the API-first developer guide markdown for UI/API clients."""
    doc_path = (_docs_dir() / "API_DOC_GUIDE.md").resolve()
    try:
        content = doc_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return jsonify({"success": False, "error": "API doc guide file not found."}), 404
    except OSError as exc:
        return jsonify({"success": False, "error": f"Could not read API doc guide: {exc}"}), 500

    return jsonify({
        "success": True,
        "api_first": True,
        "path": str(doc_path),
        "content": _sanitize_doc_text(content),
    }), 200


@settings_bp.route("/docs", methods=["GET"])
def list_docs():
    """List markdown docs available for in-app docs navigation."""
    docs_dir = _docs_dir()
    if not docs_dir.exists() or not docs_dir.is_dir():
        return jsonify({
            "success": False,
            "error": f"Docs folder not found at: {docs_dir}",
            "guidance": f"Expected docs directory at: {docs_dir}. Ensure docs folder is deployed with the application.",
            "docs_path": str(docs_dir)
        }), 404

    preferred = [
        "API_DOC_GUIDE.md",
        "DEVELOPER_GUIDE.md",
        "ARCHITECTURE.md",
        "INTEGRATION_EXAMPLES.md",
        "MICROSERVICE_SETUP.md",
        "MICROSERVICE_IMPLEMENTATION.md",
        "MICROSERVICE_QUICK_REF.md",
    ]
    all_md = sorted([p.name for p in docs_dir.glob("*.md")])
    all_md = [n for n in all_md if "FIXES" not in n.upper()]
    ordered = [n for n in preferred if n in all_md] + [n for n in all_md if n not in preferred]
    items = [
        {
            "slug": n.replace(".md", ""),
            "file": n,
            "title": _doc_title_from_name(n),
        }
        for n in ordered
    ]
    return jsonify({"success": True, "items": items}), 200


@settings_bp.route("/docs/<slug>", methods=["GET"])
def get_doc(slug: str):
    """Return markdown content for a specific docs page by slug."""
    docs_dir = _docs_dir()
    file_name = f"{slug}.md"
    doc_path = (docs_dir / file_name).resolve()

    if docs_dir not in doc_path.parents:
        return jsonify({"success": False, "error": "Invalid docs path."}), 400

    if not doc_path.exists() or not doc_path.is_file():
        return jsonify({"success": False, "error": "Doc not found."}), 404

    try:
        content = doc_path.read_text(encoding="utf-8")
    except OSError as exc:
        return jsonify({"success": False, "error": f"Could not read doc: {exc}"}), 500

    return jsonify({
        "success": True,
        "slug": slug,
        "file": file_name,
        "title": _doc_title_from_name(file_name),
        "content": _sanitize_doc_text(content),
    }), 200
