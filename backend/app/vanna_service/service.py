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

logger = logging.getLogger(__name__)

AUTH_ACCESS_MARKER = "[ACCESS:AUTHENTICATED]"


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

        engine = create_engine(db_url)

        def run_sql(sql: str):
            import pandas as pd
            with engine.connect() as conn:
                return pd.read_sql_query(text(sql), conn)

        self._vn.run_sql = run_sql
        self._vn.run_sql_is_set = True
        self._connected_db = db_url
        logger.info("✅ Vanna connected to source database for SQL execution.")

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
        
        Creates separate training records for each table in the source database,
        extracting the CREATE TABLE statement and column documentation.
        """
        from sqlalchemy import create_engine, text, inspect
        import pandas as pd

        engine = create_engine(db_url)
        inspector = inspect(engine)
        
        # Get all tables
        tables = inspector.get_table_names()
        trained_count = 0
        column_count = 0
        
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
                    
                    # Build documentation string with table name and all columns
                    col_docs = []
                    for col in columns:
                        col_name = col['name']
                        col_type = col.get('type', 'UNKNOWN')
                        col_nullable = col.get('nullable', True)
                        col_default = col.get('default')
                        
                        col_info = f"  - {col_name}: {col_type}"
                        if not col_nullable:
                            col_info += " NOT NULL"
                        if col_default:
                            col_info += f" DEFAULT {col_default}"
                        col_docs.append(col_info)
                    
                    # Create training content per table
                    training_content = f"Table: {table_name}\nColumns:\n" + "\n".join(col_docs)
                    
                    # Train Vanna with this table's documentation
                    try:
                        self._vn.train(documentation=training_content)
                        trained_count += 1
                        column_count += len(columns)
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
            "message": f"Trained on {trained_count} tables ({column_count} columns)."
        }

    def list_training_data(self):
        try:
            df = self._vn.get_training_data()
            return df.to_dict(orient="records") if df is not None and not df.empty else []
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Could not list training data: {exc}")
            return []

    def remove_training(self, vanna_id: str) -> bool:
        try:
            return bool(self._vn.remove_training_data(id=vanna_id))
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Could not remove training id {vanna_id}: {exc}")
            return False

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
                               scope_note: str = "", access_mode: str = "authenticated") -> str:
        """Generate SQL using RAG retrieval + the prior conversation turns.

        We reuse Vanna's retrieval (similar Q/SQL, related DDL, related docs) for
        the consolidated question, then assemble a prompt that ALSO includes the
        conversation turns so the model resolves references and stays on-topic.

        `scope_note` (optional) carries data-isolation instructions (company /
        branch filtering) that the LLM must apply when generating SQL.
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

    def correct_sql(self, question: str, bad_sql: str, error_message: str,
                    history: Optional[List[Dict[str, Any]]] = None) -> str:
        """Auto-correction agent: feed the failing SQL + DB error back to the LLM."""
        if not self.ready:
            raise RuntimeError("Vanna is not initialized.")
        vn = self._vn
        try:
            ddl_list = vn.get_related_ddl(question)
        except Exception:
            ddl_list = []
        ddl_text = "\n\n".join(ddl_list) if ddl_list else ""

        messages = [
            vn.system_message(
                "You are a SQL debugging expert. A query failed to execute. "
                "Rewrite it so it runs correctly. Output ONLY the corrected, "
                "single read-only SELECT statement — no commentary, no markdown."
            ),
        ]
        if ddl_text:
            messages.append(vn.user_message(f"Relevant schema (DDL):\n{ddl_text}"))
        messages.append(vn.user_message(
            f"Original question:\n{question}\n\n"
            f"SQL that failed:\n{bad_sql}\n\n"
            f"Database error message:\n{error_message}\n\n"
            "Return the corrected SQL only."
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
