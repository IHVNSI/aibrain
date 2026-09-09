"""Database migration utilities for switching between SQLite, PostgreSQL, and MySQL."""
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dotenv import load_dotenv, set_key
from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, Text, DateTime, Boolean, JSON, Float, inspect, event, text
from sqlalchemy.sql import select
from sqlalchemy.pool import StaticPool
from urllib.parse import urlparse, quote_plus
import shutil

logger = logging.getLogger(__name__)

# Get backend root directory
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


def _get_env_file() -> Path:
    """Get the absolute path to .env file."""
    if _ENV_FILE.exists():
        return _ENV_FILE
    # Try common locations
    env_path = Path(_BACKEND_DIR) / ".env"
    if env_path.exists():
        return env_path
    return _ENV_FILE


def _update_env_file(key: str, value: str) -> bool:
    """Update or create .env file with new key-value pair."""
    try:
        env_file = _get_env_file()
        if not env_file.exists():
            env_file.touch()
        set_key(str(env_file), key, value)
        # Reload dotenv
        load_dotenv(str(env_file), override=True)
        logger.info(f"Updated {key} in {env_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to update .env file: {e}")
        return False


def parse_db_url(url: str) -> Dict[str, Any]:
    """Parse database URL into components."""
    if not url:
        return {}
    
    try:
        # Handle different URL formats
        if url.startswith("sqlite"):
            parsed = urlparse(url)
            path = parsed.path
            if parsed.netloc:  # sqlite://path format
                path = parsed.netloc + parsed.path
            return {
                "type": "sqlite",
                "path": path.lstrip("/"),
            }
        elif url.startswith("postgresql"):
            parsed = urlparse(url)
            return {
                "type": "postgresql",
                "username": parsed.username,
                "password": parsed.password,
                "host": parsed.hostname or "localhost",
                "port": parsed.port or 5432,
                "database": parsed.path.lstrip("/"),
            }
        elif url.startswith("mysql"):
            parsed = urlparse(url)
            return {
                "type": "mysql",
                "username": parsed.username,
                "password": parsed.password,
                "host": parsed.hostname or "localhost",
                "port": parsed.port or 3306,
                "database": parsed.path.lstrip("/"),
            }
        else:
            parsed = urlparse(url)
            scheme = parsed.scheme.split("+")[0]
            return {
                "type": scheme,
                "username": parsed.username,
                "password": parsed.password,
                "host": parsed.hostname or "localhost",
                "port": parsed.port,
                "database": parsed.path.lstrip("/"),
                "raw_url": url,
            }
    except Exception as e:
        logger.error(f"Error parsing DB URL: {e}")
        return {}


def build_db_url(db_type: str, **kwargs) -> str:
    """Build database URL from components."""
    if db_type == "sqlite":
        path = kwargs.get("path", "assistantai.db")
        if not path.startswith("sqlite"):
            return f"sqlite:///{path}"
        return path
    elif db_type == "postgresql":
        username = quote_plus(kwargs.get("username", ""))
        password = quote_plus(kwargs.get("password", ""))
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 5432)
        database = kwargs.get("database", "assistantai")
        
        auth = f"{username}"
        if password:
            auth += f":{password}"
        auth += "@" if auth else ""
        
        return f"postgresql+psycopg2://{auth}{host}:{port}/{database}"
    elif db_type == "mysql":
        username = quote_plus(kwargs.get("username", ""))
        password = quote_plus(kwargs.get("password", ""))
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 3306)
        database = kwargs.get("database", "assistantai")
        
        auth = f"{username}"
        if password:
            auth += f":{password}"
        auth += "@" if auth else ""
        
        return f"mysql+pymysql://{auth}{host}:{port}/{database}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def test_connection(db_url: str) -> Tuple[bool, str]:
    """Test database connection."""
    try:
        if db_url.startswith("sqlite"):
            engine = create_engine(db_url, connect_args={"check_same_thread": False})
        else:
            engine = create_engine(db_url, connect_args={"timeout": 10})
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True, "Connection successful"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


def create_database_if_not_exists(db_url: str) -> Tuple[bool, str]:
    """Create database if it doesn't exist (for PostgreSQL and MySQL)."""
    try:
        parsed = parse_db_url(db_url)
        db_type = parsed.get("type")
        
        if db_type == "sqlite":
            # SQLite creates DB automatically when connecting
            return True, "SQLite database will be created on first connection"
        
        elif db_type == "postgresql":
            # Connect to default postgres database
            admin_url = build_db_url(
                "postgresql",
                username=parsed.get("username"),
                password=parsed.get("password"),
                host=parsed.get("host"),
                port=parsed.get("port"),
                database="postgres"
            )
            database_name = parsed.get("database")
            
            try:
                engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", connect_args={"timeout": 10})
                with engine.connect() as conn:
                    # Check if database exists
                    result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{database_name}'"))
                    if not result.fetchone():
                        conn.execute(text(f"CREATE DATABASE {database_name}"))
                        logger.info(f"Created PostgreSQL database: {database_name}")
                engine.dispose()
                return True, f"PostgreSQL database '{database_name}' created or already exists"
            except Exception as e:
                return False, f"Failed to create PostgreSQL database: {str(e)}"
        
        elif db_type == "mysql":
            # Connect to MySQL without database
            admin_url = build_db_url(
                "mysql",
                username=parsed.get("username"),
                password=parsed.get("password"),
                host=parsed.get("host"),
                port=parsed.get("port"),
                database=""
            )
            database_name = parsed.get("database")
            
            try:
                engine = create_engine(admin_url, connect_args={"timeout": 10})
                with engine.connect() as conn:
                    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {database_name}"))
                    logger.info(f"Created MySQL database: {database_name}")
                engine.dispose()
                return True, f"MySQL database '{database_name}' created or already exists"
            except Exception as e:
                return False, f"Failed to create MySQL database: {str(e)}"
        
        else:
            return False, f"Unsupported database type: {db_type}"
    
    except Exception as e:
        return False, f"Error creating database: {str(e)}"


def migrate_data(source_url: str, target_url: str, models_list: List[Any]) -> Tuple[bool, str, Dict[str, int]]:
    """Migrate data from source database to target database."""
    stats = {}
    try:
        # Create source and target engines
        source_engine = create_engine(
            source_url,
            connect_args={"check_same_thread": False} if source_url.startswith("sqlite") else {"timeout": 10}
        )
        target_engine = create_engine(
            target_url,
            connect_args={"check_same_thread": False} if target_url.startswith("sqlite") else {"timeout": 10}
        )
        
        # Create all tables in target database
        from .models import Base
        with target_engine.begin() as conn:
            Base.metadata.create_all(conn)
        
        # Get all tables from source
        inspector = inspect(source_engine)
        tables = inspector.get_table_names()
        
        logger.info(f"Migrating {len(tables)} tables from {source_url} to {target_url}")
        
        for table_name in tables:
            try:
                # Skip system tables
                if table_name.startswith("sqlite_"):
                    continue
                
                # Read data from source
                with source_engine.connect() as conn:
                    result = conn.execute(text(f"SELECT * FROM {table_name}"))
                    rows = result.fetchall()
                    columns = [col for col in result.keys()]
                
                # Write data to target
                if rows:
                    with target_engine.begin() as conn:
                        for row in rows:
                            row_dict = dict(zip(columns, row))
                            col_names = ', '.join([f'"{col}"' for col in columns])
                            placeholders = ', '.join([f":{col}" for col in columns])
                            insert_stmt = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
                            conn.execute(text(insert_stmt), row_dict)
                    stats[table_name] = len(rows)
                    logger.info(f"Migrated {len(rows)} rows to {table_name}")
                else:
                    stats[table_name] = 0
                    
            except Exception as e:
                logger.warning(f"Error migrating table {table_name}: {e}")
                continue
        
        source_engine.dispose()
        target_engine.dispose()
        return True, "Data migration completed", stats
    
    except Exception as e:
        logger.error(f"Data migration error: {e}")
        return False, f"Migration failed: {str(e)}", stats


def backup_database(db_url: str) -> Tuple[bool, str]:
    """Create a backup of the database before migration."""
    try:
        parsed = parse_db_url(db_url)
        db_type = parsed.get("type")
        
        if db_type == "sqlite":
            path = Path(parsed.get("path"))
            if path.exists():
                backup_path = path.parent / f"{path.stem}_backup_{Path.ctime(path):.0f}{path.suffix}"
                shutil.copy2(path, backup_path)
                logger.info(f"Created SQLite backup: {backup_path}")
                return True, f"Backup created: {backup_path}"
            else:
                return True, "SQLite database does not exist yet, no backup needed"
        else:
            # For PostgreSQL and MySQL, backups should be done separately
            return True, f"Please create a manual backup of your {db_type} database"
    
    except Exception as e:
        logger.error(f"Backup error: {e}")
        return False, f"Backup failed: {str(e)}"


def migrate_admin_db(target_db_type: str, target_url: str) -> Tuple[bool, str]:
    """
    Complete admin database migration:
    1. Create backup
    2. Create target database if needed
    3. Migrate data
    4. Update .env file
    5. Restart Flask app with new database
    """
    try:
        from .config import Config
        current_url = Config.ADMIN_DB_URL
        
        logger.info(f"Starting admin database migration from {current_url} to {target_url}")
        
        # Step 1: Backup current database
        success, msg = backup_database(current_url)
        if not success:
            return False, f"Backup failed: {msg}"
        logger.info(f"Backup: {msg}")
        
        # Step 2: Create target database
        success, msg = create_database_if_not_exists(target_url)
        if not success:
            return False, f"Database creation failed: {msg}"
        logger.info(f"Database creation: {msg}")
        
        # Step 3: Test connection to target
        success, msg = test_connection(target_url)
        if not success:
            return False, f"Cannot connect to target database: {msg}"
        logger.info(f"Target connection: {msg}")
        
        # Step 4: Migrate data using SQLAlchemy
        from .models import Base
        success, msg, stats = migrate_data(current_url, target_url, Base.metadata.tables.values())
        if not success:
            return False, f"Data migration failed: {msg}"
        logger.info(f"Data migration: {msg}")
        
        # Step 5: Update .env file
        success = _update_env_file("ADMIN_DB_URL", target_url)
        if not success:
            return False, "Failed to update .env file"
        logger.info(f"Updated .env with new ADMIN_DB_URL")
        
        return True, f"Database migration successful. Migrated {len(stats)} tables: {stats}"
    
    except Exception as e:
        logger.error(f"Database migration error: {e}")
        return False, f"Migration error: {str(e)}"


def get_db_info(db_url: str) -> Dict[str, Any]:
    """Get information about a database."""
    try:
        # Always parse the URL first to get the database type
        parsed = parse_db_url(db_url)
        db_type = parsed.get("type", "unknown")
        
        info = {
            "type": db_type,
            "url": db_url,
        }
        
        # Try to test the connection
        success, msg = test_connection(db_url)
        info["accessible"] = success
        if not success:
            info["error"] = msg
            return info
        
        if db_type == "sqlite":
            path_str = parsed.get("path", "assistantai.db")
            # If path is relative, resolve it relative to backend directory
            if not Path(path_str).is_absolute():
                path_str = str(_BACKEND_DIR / path_str)
            path = Path(path_str)
            if path.exists():
                info["size_bytes"] = path.stat().st_size
                info["path"] = str(path)
            else:
                # SQLite file may be created on first connection
                info["path"] = str(path)
                info["size_bytes"] = 0
        elif db_type in ["postgresql", "mysql"]:
            info["host"] = parsed.get("host")
            info["port"] = parsed.get("port")
            info["database"] = parsed.get("database")
        
        # Get table count
        try:
            engine = create_engine(db_url, connect_args={"check_same_thread": False} if db_type == "sqlite" else {})
            inspector = inspect(engine)
            info["table_count"] = len(inspector.get_table_names())
            engine.dispose()
        except Exception:
            info["table_count"] = 0
        
        return info
    
    except Exception as e:
        logger.error(f"Error getting DB info: {e}")
        return {"type": "unknown", "accessible": False, "error": str(e)}


def validate_db_url(db_type: str, **kwargs) -> Tuple[bool, str]:
    """Validate database URL parameters before migration."""
    errors = []
    
    if db_type == "sqlite":
        path = kwargs.get("path", "").strip()
        if not path:
            errors.append("SQLite path is required")
    elif db_type == "postgresql":
        if not kwargs.get("database", "").strip():
            errors.append("Database name is required for PostgreSQL")
        if not kwargs.get("host", "").strip():
            errors.append("Host is required for PostgreSQL")
    elif db_type == "mysql":
        if not kwargs.get("database", "").strip():
            errors.append("Database name is required for MySQL")
        if not kwargs.get("host", "").strip():
            errors.append("Host is required for MySQL")
    else:
        errors.append(f"Unsupported database type: {db_type}")
    
    if errors:
        return False, "; ".join(errors)
    return True, "Validation passed"
