"""Vanna.ai text-to-SQL service.

Combines a selectable Vanna vector store (ChromaDB / FAISS / Pinecone) with our
pluggable LLM provider layer (HF offline / OpenAI / Gemini / Claude), and adds
multi-turn conversational SQL generation.

Vanna's `VannaBase` defines the abstract LLM hooks (`system_message`,
`user_message`, `assistant_message`, `submit_prompt`) and the vector-store
mixins implement training + retrieval (`add_ddl`, `add_documentation`,
`add_question_sql`, `get_related_ddl`, `get_related_documentation`,
`get_similar_question_sql`). We bridge `submit_prompt` to our LLMProvider so any
backend works, then layer conversation history on top for multi-turn.
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, date, time
from sqlalchemy import event

logger = logging.getLogger(__name__)

AUTH_ACCESS_MARKER = "[ACCESS:AUTHENTICATED]"


def _make_json_serializable(obj):
    """Convert non-JSON-serializable objects (Timestamp, datetime, etc.) to strings."""
    try:
        # Try to import pandas Timestamp if pandas is available
        import pandas as pd
        if isinstance(obj, (pd.Timestamp, datetime, date, time)):
            return obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
    except ImportError:
        # pandas not available, fall through to datetime check
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
    
    # Handle other types
    if hasattr(obj, '__dict__'):
        return str(obj)
    return obj


def _convert_rows_to_serializable(rows):
    """Convert all values in rows to JSON-serializable types."""
    if not rows:
        return rows
    
    serializable_rows = []
    for row in rows:
        serializable_row = {}
        for key, value in row.items():
            if value is None or isinstance(value, (str, int, float, bool)):
                serializable_row[key] = value
            else:
                # Convert non-serializable types
                serializable_row[key] = _make_json_serializable(value)
        serializable_rows.append(serializable_row)
    
    return serializable_rows


def _convert_sql_dialect(sql: str, db_url: str) -> str:
    """
    Convert SQL to match the target database dialect.
    Currently handles SQLite → MySQL conversions when executing on MySQL.
    
    Args:
        sql: Original SQL statement
        db_url: Database connection URL to detect dialect
    
    Returns:
        Converted SQL statement (or original if no conversion needed)
    """
    if not db_url:
        return sql
    
    # Detect target database dialect from URL
    db_url_lower = db_url.lower()
    is_mysql = any(marker in db_url_lower for marker in ["mysql+", "mysql://", "+pymysql"])
    is_postgres = any(marker in db_url_lower for marker in ["postgresql+", "postgres://", "postgresql://"])
    
    # If target is MySQL, convert from SQLite syntax
    if is_mysql:
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
        
        logger.debug("✓ Converted SQL from SQLite to MySQL dialect")
    
    elif is_postgres:
        import re
        
        # SQLite → PostgreSQL conversions if needed
        # datetime('now') → NOW()
        sql = re.sub(r"datetime\s*\(\s*'now'\s*\)", r"NOW()", sql, flags=re.IGNORECASE)
        
        # date('now') → CURRENT_DATE
        sql = re.sub(r"date\s*\(\s*'now'\s*\)", r"CURRENT_DATE", sql, flags=re.IGNORECASE)
        
        logger.debug("✓ Converted SQL from SQLite to PostgreSQL dialect")
    
    return sql


def _build_vanna_class(vector_store: str):
    """Return a Vanna class combining the requested vector store with our LLM bridge."""
    from vanna.base import VannaBase

    # ---- LLM bridge mixin: routes Vanna prompts to our LLMProvider ---- #
    class _LLMBridge(VannaBase):
        def __init__(self, config=None):
            VannaBase.__init__(self, config=config)
            self._llm = (config or {}).get("llm_provider")

        def set_llm(self, llm_provider):
            self._llm = llm_provider

        def system_message(self, message: str) -> Any:
            return {"role": "system", "content": message}

        def user_message(self, message: str) -> Any:
            return {"role": "user", "content": message}

        def assistant_message(self, message: str) -> Any:
            return {"role": "assistant", "content": message}

        def submit_prompt(self, prompt, **kwargs) -> str:
            if self._llm is None:
                raise RuntimeError("No LLM provider configured for Vanna.")
            # Vanna passes a list of {role, content} dicts — our providers accept that.
            return self._llm.chat(prompt, **kwargs)

    vs = (vector_store or "chromadb").lower()
    if vs == "faiss":
        try:
            from vanna.faiss import FAISS as _Store  # type: ignore
        except Exception:  # pragma: no cover - optional dep / version differences
            logger.warning("FAISS Vanna store unavailable; falling back to ChromaDB")
            from vanna.chromadb import ChromaDB_VectorStore as _Store
    elif vs == "pinecone":
        try:
            from vanna.pinecone import PineconeDB_VectorStore as _Store  # type: ignore
        except Exception:
            logger.warning("Pinecone Vanna store unavailable; falling back to ChromaDB")
            from vanna.chromadb import ChromaDB_VectorStore as _Store
    else:
        from vanna.chromadb import ChromaDB_VectorStore as _Store

    class _Vanna(_Store, _LLMBridge):
        def __init__(self, config=None):
            _Store.__init__(self, config=config)
            _LLMBridge.__init__(self, config=config)

    return _Vanna


class VannaService:
    """High-level wrapper used by the API layer."""

    def __init__(self):
        self._vn = None
        self._llm = None
        self._vector_store = None
        self._connected_db = None
        self._init_error: Optional[str] = None
        self.last_context_cache: Dict[str, Any] = {}

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def initialize(self, llm_provider, vector_store: str, vs_config: Dict[str, Any]):
        """(Re)build the Vanna instance with the given LLM + vector store."""
        try:
            VannaClass = _build_vanna_class(vector_store)
            config = dict(vs_config or {})
            config["llm_provider"] = llm_provider
            self._vn = VannaClass(config=config)
            self._llm = llm_provider
            self._vector_store = vector_store
            self._init_error = None
            logger.info(f"✅ Vanna initialized (vector_store={vector_store}, llm={getattr(llm_provider,'name',None)})")
            return True
        except Exception as exc:  # noqa: BLE001
            self._init_error = f"{type(exc).__name__}: {exc}"
            logger.error(f"Vanna initialization failed: {self._init_error}")
            self._vn = None
            return False

    @property
    def ready(self) -> bool:
        return self._vn is not None and self._llm is not None

    def status(self) -> Dict[str, Any]:
        return {
            "ready": self.ready,
            "vector_store": self._vector_store,
            "llm_provider": getattr(self._llm, "name", None),
            "llm_model": getattr(self._llm, "model", None),
            "connected_db": bool(self._connected_db),
            "init_error": self._init_error,
        }

    # ------------------------------------------------------------------ #
    # Source DB connection (for running generated SQL)
    # ------------------------------------------------------------------ #
    def connect_db(self, db_url: str):
        """Connect Vanna's run_sql to the source database via SQLAlchemy."""
        if not self.ready:
            raise RuntimeError("Vanna is not initialized.")
        from sqlalchemy import create_engine, text
        import time

        # Create engine with extended timeout for complex queries
        # SQLite and other databases need different connection parameters
        connect_args = {}
        db_url_lower = db_url.lower()
        is_sqlite = "sqlite" in db_url_lower
        is_mysql = "mysql" in db_url_lower or "pymysql" in db_url_lower
        is_postgres = "postgresql" in db_url_lower or "psycopg2" in db_url_lower
        
        if is_sqlite:
            # SQLite: only use check_same_thread, NOT timeout (causes connection issues)
            # Timeout is handled at connection level, not in connect_args
            connect_args = {"check_same_thread": False}
        elif is_mysql:
            # MySQL: use connect_timeout (not timeout) for connection establishment
            connect_args = {"connect_timeout": 30}
        elif is_postgres:
            # PostgreSQL: use connect_timeout for connection establishment
            connect_args = {"connect_timeout": 30}
        
        # Create engine
        engine = create_engine(db_url, connect_args=connect_args)
        
        # For SQLite, set timeout on the raw connection
        if is_sqlite:
            @event.listens_for(engine, "connect")
            def set_sqlite_timeout(dbapi_conn, connection_record):
                dbapi_conn.timeout = 30

        def run_sql(sql: str):
            import pandas as pd
            # Apply dialect conversion if needed
            converted_sql = _convert_sql_dialect(sql, db_url)
            
            start_time = time.time()
            try:
                with engine.connect() as conn:
                    df = pd.read_sql_query(text(converted_sql), conn)
                    execution_time = time.time() - start_time
                    row_count = len(df) if df is not None else 0
                    logger.info(f"✅ Query executed in {execution_time:.2f}s, returned {row_count} rows")
                    return df
            except Exception as exc:
                execution_time = time.time() - start_time
                error_str = str(exc).lower()
                if "timeout" in error_str or "timed out" in error_str or "database is locked" in error_str:
                    logger.error(f"⏱️  Query TIMEOUT after {execution_time:.2f}s: {str(exc)[:200]}")
                else:
                    logger.error(f"❌ Query failed after {execution_time:.2f}s: {str(exc)[:200]}")
                raise

        self._vn.run_sql = run_sql
        self._vn.run_sql_is_set = True
        self._connected_db = db_url
        self._engine = engine  # Store engine for DML operations
        logger.info("✅ Vanna connected to source database for SQL execution (30s query timeout).")

    def execute_dml(self, sql: str) -> Dict[str, Any]:
        """Execute DML queries (INSERT, UPDATE, DELETE) and return affected rows count.
        
        Returns dict with:
        - success: bool
        - affected_rows: int
        - message: str
        - error: optional error message
        """
        if not self._connected_db or not hasattr(self, '_engine'):
            raise RuntimeError("No source database connected.")
        
        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.pool import NullPool
            
            # Create fresh connection for DML execution
            connect_args = {}
            db_url_lower = self._connected_db.lower()
            is_sqlite = "sqlite" in db_url_lower
            is_mysql = "mysql" in db_url_lower or "pymysql" in db_url_lower
            is_postgres = "postgresql" in db_url_lower or "psycopg2" in db_url_lower
            
            if is_sqlite:
                # SQLite: only use check_same_thread, NOT timeout in connect_args
                connect_args = {"check_same_thread": False}
            elif is_mysql:
                # MySQL: use connect_timeout (not timeout) for connection establishment
                connect_args = {"connect_timeout": 30}
            elif is_postgres:
                # PostgreSQL: use connect_timeout for connection establishment
                connect_args = {"connect_timeout": 30}
            
            engine = create_engine(self._connected_db, connect_args=connect_args, poolclass=NullPool)
            
            # For SQLite, set timeout on the raw connection
            if is_sqlite:
                @event.listens_for(engine, "connect")
                def set_sqlite_timeout(dbapi_conn, connection_record):
                    dbapi_conn.timeout = 30
            
            converted_sql = _convert_sql_dialect(sql, self._connected_db)
            
            with engine.begin() as conn:  # Auto-commit on success
                result = conn.execute(text(converted_sql))
                affected_rows = result.rowcount or 0
                
                # Determine operation type
                op_type = "unknown"
                sql_upper = converted_sql.strip().upper()
                if sql_upper.startswith("INSERT"):
                    op_type = "inserted"
                elif sql_upper.startswith("UPDATE"):
                    op_type = "updated"
                elif sql_upper.startswith("DELETE"):
                    op_type = "deleted"
                
                logger.info(f"✅ DML executed: {op_type} {affected_rows} rows")
                return {
                    "success": True,
                    "affected_rows": affected_rows,
                    "message": f"Successfully {op_type} {affected_rows} row(s).",
                    "error": None
                }
        except Exception as exc:
            error_msg = str(exc)
            logger.error(f"❌ DML execution failed: {error_msg}")
            return {
                "success": False,
                "affected_rows": 0,
                "message": None,
                "error": error_msg
            }

    # ------------------------------------------------------------------ #
    # Training (RAG)
    # ------------------------------------------------------------------ #
    def train_ddl(self, ddl: str) -> str:
        return self._vn.train(ddl=ddl)

    def train_documentation(self, documentation: str) -> str:
        return self._vn.train(documentation=documentation)

    def train_sql(self, question: str, sql: str) -> str:
        return self._vn.train(question=question, sql=sql)

    def train_from_information_schema(self, db_url: str) -> Dict[str, Any]:
        """Auto-train on the source DB's INFORMATION_SCHEMA (per-table DDL generation).
        
        Returns detailed DDL for each table so user can view and edit schemas manually.
        """
        from sqlalchemy import create_engine, text, inspect, MetaData, Table
        from sqlalchemy.schema import CreateTable

        engine = create_engine(db_url)
        inspector = inspect(engine)
        metadata = MetaData()
        
        # Get all tables
        tables = inspector.get_table_names()
        trained_count = 0
        column_count = 0
        table_ddls = []  # Collect DDL for each table
        
        with engine.connect() as conn:
            for table_name in tables:
                try:
                    # Skip system/metadata tables
                    if table_name.lower().startswith(('sqlite_', 'information_schema', 'mysql_', 'pg_')):
                        continue
                    
                    # Get columns for this table
                    columns = inspector.get_columns(table_name)
                    if not columns:
                        continue
                    
                    # Try to get CREATE TABLE DDL
                    ddl_text = None
                    try:
                        # Try SQLAlchemy's DDL compiler
                        table = Table(table_name, metadata, autoload_with=engine)
                        ddl_text = str(CreateTable(table).compile(engine))
                    except Exception as e:
                        logger.debug(f"Could not compile DDL for {table_name}: {e}")
                        
                        # Fallback: build documentation string with table info
                        col_docs = []
                        for col in columns:
                            col_name = col['name']
                            col_type = str(col.get('type', 'UNKNOWN'))
                            col_nullable = col.get('nullable', True)
                            col_default = col.get('default')
                            
                            col_info = f"  {col_name}: {col_type}"
                            if not col_nullable:
                                col_info += " NOT NULL"
                            if col_default:
                                col_info += f" DEFAULT {col_default}"
                            col_docs.append(col_info)
                        
                        ddl_text = f"-- Table: {table_name}\n-- Columns:\n" + "\n".join(col_docs)
                    
                    # Train Vanna with this table's DDL
                    try:
                        vanna_id = self._vn.train(ddl=ddl_text)
                        trained_count += 1
                        column_count += len(columns)
                        table_ddls.append({
                            'table_name': table_name,
                            'column_count': len(columns),
                            'ddl': ddl_text,
                            'vanna_id': str(vanna_id)
                        })
                        logger.debug(f"✓ Trained on table '{table_name}' ({len(columns)} columns)")
                    except Exception as e:
                        logger.warning(f"Failed to train on table '{table_name}': {e}")
                        continue
                        
                except Exception as e:
                    logger.warning(f"Error processing table '{table_name}': {e}")
                    continue
        
        return {
            "items": trained_count,
            "columns": column_count,
            "message": f"Trained on {trained_count} tables ({column_count} columns).",
            "tables": table_ddls  # List of {table_name, column_count, ddl, vanna_id}
        }

    def list_training_data(self):
        try:
            df = self._vn.get_training_data()
            rows = df.to_dict(orient="records") if df is not None and not df.empty else []
            # Convert any non-JSON-serializable objects (Timestamp, datetime, etc.) to strings
            rows = _convert_rows_to_serializable(rows)
            return rows
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Could not list training data: {exc}")
            return []

    def remove_training(self, vanna_id: str) -> bool:
        try:
            return bool(self._vn.remove_training_data(id=vanna_id))
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Could not remove training id {vanna_id}: {exc}")
            return False

    def clear_all_training(self) -> int:
        """Clear all training data from Vanna (used when switching databases)."""
        try:
            training_data = self.list_training_data()
            if not training_data:
                logger.info("No training data to clear")
                return 0
            
            cleared_count = 0
            for item in training_data:
                item_id = item.get('id')
                if item_id and self.remove_training(item_id):
                    cleared_count += 1
            
            logger.info(f"✓ Cleared {cleared_count} training items from Vanna")
            return cleared_count
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Error clearing training data: {exc}")
            return 0

    def get_valid_tables(self) -> set:
        """Get list of actual table names in the connected source database."""
        if not self._connected_db:
            return set()
        try:
            from sqlalchemy import create_engine, inspect
            engine = create_engine(self._connected_db)
            inspector = inspect(engine)
            tables = set(inspector.get_table_names())
            logger.debug(f"Valid tables in database: {tables}")
            return tables
        except Exception as exc:
            logger.warning(f"Could not get table names: {exc}")
            return set()

    def validate_sql_tables(self, sql: str) -> tuple[bool, str]:
        """Check if SQL references valid tables. Returns (is_valid, error_message)."""
        try:
            from sqlalchemy import text, create_engine
            import re
            
            valid_tables = self.get_valid_tables()
            if not valid_tables:
                # Can't validate without knowing valid tables
                return True, ""
            
            # Extract table names from SQL using regex (simplistic but effective)
            # Matches: FROM table, JOIN table, INTO table, UPDATE table
            pattern = r'\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+(?:(?:\w+\.)?(\w+))'
            referenced_tables = set()
            for match in re.finditer(pattern, sql, re.IGNORECASE):
                table_name = match.group(1)
                if table_name and not table_name.upper() in ('SELECT', 'WHERE'):
                    referenced_tables.add(table_name.lower())
            
            # Check if all referenced tables exist
            valid_lower = {t.lower() for t in valid_tables}
            invalid_tables = referenced_tables - valid_lower
            
            if invalid_tables:
                return False, f"SQL references non-existent tables: {', '.join(sorted(invalid_tables))}"
            
            return True, ""
        except Exception as exc:
            logger.debug(f"SQL validation error: {exc}")
            return True, ""  # Don't fail if validation itself fails

    def get_valid_columns(self, table_name: str) -> set:
        """Get list of actual column names for a specific table."""
        if not self._connected_db:
            return set()
        try:
            from sqlalchemy import create_engine, inspect
            engine = create_engine(self._connected_db)
            inspector = inspect(engine)
            columns = {c['name'].lower() for c in inspector.get_columns(table_name)}
            logger.debug(f"Valid columns in table '{table_name}': {columns}")
            return columns
        except Exception as exc:
            logger.debug(f"Could not get columns for table '{table_name}': {exc}")
            return set()

    def validate_sql_columns(self, sql: str) -> tuple[bool, str]:
        """Check if SQL references valid columns. Returns (is_valid, error_message).
        
        This prevents "Unknown column" errors by validating column names exist
        in the referenced tables before execution.
        """
        if not self._connected_db:
            return True, ""  # Can't validate without DB connection
        
        try:
            from sqlalchemy import text, create_engine, inspect
            import re
            
            engine = create_engine(self._connected_db)
            inspector = inspect(engine)
            
            # Extract table references and their columns
            # Match patterns like: table.column or just column (when table context is clear)
            sql_upper = sql.upper()
            
            # Extract FROM/JOIN clauses with their tables
            from_pattern = r'\b(?:FROM|JOIN)\s+(?:(?:`?(\w+)`?|(\w+\s+(?:AS\s+)?(\w+))))'
            
            referenced_columns = set()
            invalid_columns = []
            
            # Extract table names from FROM and JOIN clauses
            valid_tables = {t.lower() for t in inspector.get_table_names()}
            
            # Find all table.column or column references
            column_pattern = r'(?:(\w+)\.)?(\w+)'
            
            # Look for columns in SELECT, WHERE, and other clauses
            # This is a simplified approach - looks for word.word patterns
            for match in re.finditer(r'(?<![a-zA-Z_])\w+\.\w+(?![a-zA-Z_])', sql):
                full_ref = match.group()
                parts = full_ref.split('.')
                if len(parts) == 2:
                    table_name, column_name = parts
                    table_name_lower = table_name.lower()
                    column_name_lower = column_name.lower()
                    
                    # Check if table exists
                    if table_name_lower in valid_tables:
                        try:
                            valid_cols = self.get_valid_columns(table_name_lower)
                            if valid_cols and column_name_lower not in valid_cols:
                                invalid_columns.append(f"{table_name}.{column_name}")
                        except Exception:
                            pass  # Skip validation for this column if we can't get schema
            
            if invalid_columns:
                return False, f"SQL references non-existent columns: {', '.join(sorted(invalid_columns))}"
            
            return True, ""
        except Exception as exc:
            logger.debug(f"Column validation error: {exc}")
            return True, ""  # Don't fail if validation itself fails

    # ------------------------------------------------------------------ #
    # SQL generation (single + multi-turn)
    # ------------------------------------------------------------------ #
    def generate_sql(self, question: str) -> str:
        if not self.ready:
            raise RuntimeError("Vanna is not initialized.")
        return self._vn.generate_sql(question=question)

    @staticmethod
    def _is_auth_only(text: Any) -> bool:
        return isinstance(text, str) and text.strip().startswith(AUTH_ACCESS_MARKER)

    @staticmethod
    def _strip_access_marker(text: Any) -> Any:
        if not isinstance(text, str):
            return text
        cleaned = text.strip()
        if cleaned.startswith(AUTH_ACCESS_MARKER):
            return cleaned[len(AUTH_ACCESS_MARKER):].lstrip()
        return text

    def get_related_knowledge(self, question: str, access_mode: str = "authenticated", limit: int = 8) -> List[str]:
        if not self.ready:
            return []
        try:
            docs = self._vn.get_related_documentation(question)
        except Exception:
            docs = []

        docs = docs or []
        if (access_mode or "").lower() == "guest":
            docs = [d for d in docs if not self._is_auth_only(d)]

        docs = [self._strip_access_marker(d) for d in docs]
        docs = [d for d in docs if isinstance(d, str) and d.strip()]
        return docs[: max(1, int(limit or 8))]

    def generate_sql_multiturn(self, question: str, history: List[Dict[str, Any]],
                               scope_note: str = "", access_mode: str = "authenticated",
                               is_admin: bool = False) -> str:
        """Generate SQL using RAG retrieval + the prior conversation turns.

        We reuse Vanna's retrieval (similar Q/SQL, related DDL, related docs) for
        the consolidated question, then assemble a prompt that ALSO includes the
        conversation turns so the model resolves references and stays on-topic.

        `scope_note` (optional) carries data-isolation instructions (company /
        branch filtering) that the LLM must apply when generating SQL.
        
        `is_admin` (optional) allows CRUD operations (INSERT/UPDATE/DELETE) when True.
        """
        if not self.ready:
            raise RuntimeError("Vanna is not initialized.")

        vn = self._vn
        try:
            question_sql_list = vn.get_similar_question_sql(question)
        except Exception:
            question_sql_list = []
        try:
            ddl_list = vn.get_related_ddl(question)
        except Exception:
            ddl_list = []
        try:
            doc_list = vn.get_related_documentation(question)
        except Exception:
            doc_list = []

        if (access_mode or "").lower() == "guest":
            question_sql_list = [x for x in (question_sql_list or []) if not self._is_auth_only(x)]
            ddl_list = [x for x in (ddl_list or []) if not self._is_auth_only(x)]
            doc_list = [x for x in (doc_list or []) if not self._is_auth_only(x)]

        question_sql_list = [self._strip_access_marker(x) for x in (question_sql_list or [])]
        ddl_list = [self._strip_access_marker(x) for x in (ddl_list or [])]
        doc_list = [self._strip_access_marker(x) for x in (doc_list or [])]

        self.last_context_cache = {
            "question_sql_count": len(question_sql_list or []),
            "ddl_count": len(ddl_list or []),
            "documentation_count": len(doc_list or []),
            "history_messages_used": len((history or [])[-12:]),
            "question_sql_preview": (question_sql_list or [])[:2],
            "ddl_preview": (ddl_list or [])[:2],
            "documentation_preview": (doc_list or [])[:2],
        }

        # Base prompt assembled by Vanna (system + trained context + question).
        prompt = vn.get_sql_prompt(
            initial_prompt=None,
            question=question,
            question_sql_list=question_sql_list,
            ddl_list=ddl_list,
            doc_list=doc_list,
        )

        # ===== Add explicit list of valid tables to prevent hallucinations =====
        # Get all available tables in the source database and add them to the system prompt.
        # This forces the LLM to only reference tables that actually exist.
        valid_tables = self.get_valid_tables()
        tables_list_msg = ""
        if valid_tables:
            sorted_tables = sorted(valid_tables)
            tables_list_msg = (
                f"📋 AVAILABLE TABLES IN DATABASE ({len(sorted_tables)}): {', '.join(sorted_tables)}\n"
                f"⚠️ YOU MUST ONLY REFERENCE THESE TABLES ABOVE. Any reference to tables not in this list is INVALID.\n"
                f"❌ NEVER generate SQL that references tables outside this list."
            )
            # Insert this as a system message early in the prompt
            if isinstance(prompt, list) and len(prompt) > 0:
                # Insert after system message (position 1) if it exists
                prompt.insert(1, vn.system_message(tables_list_msg))
            else:
                # Or prepend if structure is different
                if isinstance(prompt, list):
                    prompt.insert(0, vn.system_message(tables_list_msg))

        # Inject conversation history as prior messages BEFORE the final question,
        # so multi-turn references resolve. History is reference context only.
        convo_msgs = []
        for m in (history or [])[-12:]:
            if m.get("type") == "user":
                convo_msgs.append(vn.user_message(m.get("content", "")))
            elif m.get("type") == "ai":
                text = m.get("content", "")
                if m.get("sql_query"):
                    text = f"{text}\n[SQL generated earlier (reference only): {m['sql_query']}]"
                convo_msgs.append(vn.assistant_message(text))

        if convo_msgs and isinstance(prompt, list) and len(prompt) >= 1:
            # prompt[0] is the system message; keep it first, then history, then the rest.
            merged = [prompt[0]] + convo_msgs + prompt[1:]
        else:
            merged = prompt

        # ===== Chain-of-Thought + strict negative constraints =====
        # Guide the model's logical path and ban destructive output. Appended as
        # a final user instruction so it applies to THIS generation.
        if is_admin:
            # Admins can perform CRUD operations
            cot_text = (
                "Think step by step before answering: (1) identify the required "
                "tables from the schema above, (2) define the JOIN conditions using "
                "the real foreign keys, (3) apply the correct filters/aggregations, "
                "(4) then output ONLY the final SQL.\n"
                "CONSTRAINTS: Generate a single SQL statement. You MAY use SELECT (read), "
                "INSERT (create), UPDATE (modify), or DELETE (remove) statements as appropriate "
                "to fulfill the user's request. NEVER use DROP, ALTER, CREATE (for tables), "
                "TRUNCATE, GRANT, REVOKE, PRAGMA, or other system-level commands. Use ONLY "
                "tables/columns that appear in the provided schema. Add LIMIT 100 "
                "to SELECT statements unless the question implies a single aggregate value."
            )
        else:
            # Regular users are restricted to read-only
            cot_text = (
                "Think step by step before answering: (1) identify the required "
                "tables from the schema above, (2) define the JOIN conditions using "
                "the real foreign keys, (3) apply the correct filters/aggregations, "
                "(4) then output ONLY the final SQL.\n"
                "CONSTRAINTS: Generate a single READ-ONLY SELECT statement. NEVER use "
                "INSERT, UPDATE, DELETE, DROP, ALTER, CREATE or TRUNCATE. Use ONLY "
                "tables/columns that appear in the provided schema. Add LIMIT 100 "
                "unless the question implies a single aggregate value."
            )
        if scope_note:
            cot_text += "\n\n" + scope_note
        cot = vn.user_message(cot_text)
        if isinstance(merged, list):
            merged = merged + [cot]

        llm_response = vn.submit_prompt(merged)
        return vn.extract_sql(llm_response)

    def _parse_db_error(self, error_message: str) -> Dict[str, Optional[str]]:
        """Parse database error messages to extract table and column names.
        
        Handles common error patterns:
        - MySQL: "Unknown column 'col_name' in 'where clause'"
        - MySQL: "Unknown table 't1' in on clause"
        - PostgreSQL: "column \"col_name\" does not exist"
        
        Returns dict with 'table' and 'column' keys (None if not found).
        """
        import re
        result = {"table": None, "column": None}
        
        error_lower = error_message.lower()
        
        # MySQL: Unknown column 'col_name' in 'where clause'
        match = re.search(r"unknown column ['\"]([^'\"]+)['\"]", error_lower)
        if match:
            result["column"] = match.group(1)
        
        # MySQL: Unknown table 't1' in on clause
        match = re.search(r"unknown table ['\"]?([a-zA-Z0-9_]+)['\"]?", error_lower)
        if match and not result["table"]:
            result["table"] = match.group(1)
        
        # PostgreSQL: column "col_name" does not exist
        match = re.search(r'column ["\']([^"\']+)["\'] does not exist', error_lower)
        if match:
            result["column"] = match.group(1)
        
        # Try to extract table from SQL if error parsing didn't find it
        if not result["table"]:
            # Look for FROM or JOIN table references
            sql_match = re.search(r'(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)', error_message, re.IGNORECASE)
            if sql_match:
                result["table"] = sql_match.group(1)
        
        return result

    def _get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get complete schema information for a specific table.
        
        Returns dict with 'columns' list and 'column_types' dict.
        """
        if not self._connected_db:
            return {"columns": [], "column_types": {}, "error": "No database connected"}
        
        try:
            from sqlalchemy import create_engine, inspect
            engine = create_engine(self._connected_db)
            inspector = inspect(engine)
            
            # Get columns for this table
            columns = inspector.get_columns(table_name)
            if not columns:
                return {"columns": [], "column_types": {}, "error": f"Table '{table_name}' not found or has no columns"}
            
            column_names = [col['name'] for col in columns]
            column_types = {col['name']: str(col.get('type', 'UNKNOWN')) for col in columns}
            
            logger.debug(f"Table '{table_name}' schema: {column_names}")
            return {
                "columns": column_names,
                "column_types": column_types,
                "error": None
            }
        except Exception as exc:
            logger.warning(f"Error getting schema for table '{table_name}': {exc}")
            return {"columns": [], "column_types": {}, "error": str(exc)}

    def correct_sql(self, question: str, bad_sql: str, error_message: str,
                    history: Optional[List[Dict[str, Any]]] = None) -> str:
        """Auto-correction agent: feed the failing SQL + DB error back to the LLM.
        
        Enhanced with:
        - Explicit list of valid tables
        - Actual column names from the affected table (when error is column-related)
        - Structured schema information to prevent hallucination
        """
        if not self.ready:
            raise RuntimeError("Vanna is not initialized.")
        vn = self._vn
        
        # Get related DDL from vector store
        try:
            ddl_list = vn.get_related_ddl(question)
        except Exception:
            ddl_list = []
        ddl_text = "\n\n".join(ddl_list) if ddl_list else ""

        messages = [
            vn.system_message(
                "You are a SQL debugging expert. A query failed to execute. "
                "Rewrite it so it runs correctly. Output ONLY the corrected, "
                "single read-only SELECT statement — no commentary, no markdown.\n\n"
                "⚠️ CRITICAL: Only use columns and tables that actually exist in the database. "
                "Do not guess or invent column names."
            ),
        ]
        
        # ===== Parse the error to identify the specific problem =====
        error_info = self._parse_db_error(error_message)
        affected_table = error_info.get("table")
        problem_column = error_info.get("column")
        
        # ===== Add list of valid tables =====
        valid_tables = self.get_valid_tables()
        if valid_tables:
            sorted_tables = sorted(valid_tables)
            tables_msg = (
                f"📋 AVAILABLE TABLES IN DATABASE ({len(sorted_tables)}): {', '.join(sorted_tables)}\n"
                f"⚠️ IMPORTANT: Use ONLY these tables when correcting the SQL. "
                f"Do NOT introduce table names not in this list."
            )
            messages.append(vn.system_message(tables_msg))
        
        # ===== If we detected a column error, provide the actual schema for that table =====
        if problem_column and affected_table:
            schema_info = self._get_table_schema(affected_table)
            if schema_info.get("columns"):
                available_cols = schema_info["columns"]
                col_types_str = ", ".join([f"{c} ({schema_info['column_types'].get(c, '?')})" for c in available_cols])
                schema_msg = (
                    f"⚠️ ERROR DETAILS: Column '{problem_column}' doesn't exist in table '{affected_table}'\n\n"
                    f"📊 ACTUAL COLUMNS IN TABLE '{affected_table.upper()}':\n{col_types_str}\n\n"
                    f"Use one of these column names instead of '{problem_column}'."
                )
                messages.append(vn.system_message(schema_msg))
                logger.info(f"Provided schema correction for table '{affected_table}': {available_cols}")
        
        # ===== Add related DDL and error context =====
        if ddl_text:
            messages.append(vn.user_message(f"Relevant schema (DDL):\n{ddl_text}"))
        
        messages.append(vn.user_message(
            f"Original question:\n{question}\n\n"
            f"SQL that failed:\n{bad_sql}\n\n"
            f"Database error message:\n{error_message}\n\n"
            "Instructions:\n"
            "1. Identify what went wrong (column not found, table not found, etc.)\n"
            "2. Use only the column names provided above for the affected table\n"
            "3. Return the corrected SELECT statement only, no explanation"
        ))
        
        llm_response = vn.submit_prompt(messages)
        return vn.extract_sql(llm_response)

    def run_sql(self, sql: str):
        if not self.ready or not self._connected_db:
            raise RuntimeError("No source database connected.")
        return self._vn.run_sql(sql)


# Singleton
_service: Optional[VannaService] = None


def get_vanna_service() -> VannaService:
    global _service
    if _service is None:
        _service = VannaService()
    return _service
