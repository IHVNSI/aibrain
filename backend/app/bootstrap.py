"""Bootstrap helpers: build the active LLM + Vanna service from settings/env."""
import logging

from .config import Config
from .models import Setting
from .llm import build_llm, get_llm_settings
from .vanna_service import get_vanna_service

logger = logging.getLogger(__name__)


def get_vector_settings() -> dict:
    saved = Setting.get("vector_config") or {}
    return {
        "store": saved.get("store", Config.VECTOR_STORE),
        "chroma_path": saved.get("chroma_path", Config.CHROMA_PATH),
        "faiss_path": saved.get("faiss_path", Config.FAISS_PATH),
        "pinecone_api_key": saved.get("pinecone_api_key") or Config.PINECONE_API_KEY,
        "pinecone_index": saved.get("pinecone_index", Config.PINECONE_INDEX),
        "pinecone_environment": saved.get("pinecone_environment", Config.PINECONE_ENVIRONMENT),
        "embedding_model": saved.get("embedding_model", Config.EMBEDDING_MODEL),
    }


def get_db_settings() -> dict:
    saved = Setting.get("db_config") or {}
    return {"source_db_url": saved.get("source_db_url") or Config.SOURCE_DB_URL}


def _vector_config_for(store: str, vs: dict) -> dict:
    """Map our settings to the config keys Vanna's vector store expects."""
    store = (store or "chromadb").lower()
    if store == "chromadb":
        return {"path": vs["chroma_path"]}
    if store == "faiss":
        return {"path": vs["faiss_path"]}
    if store == "pinecone":
        return {
            "api_key": vs["pinecone_api_key"],
            "index_name": vs["pinecone_index"],
            "environment": vs["pinecone_environment"],
        }
    return {"path": vs.get("chroma_path", "./vanna_chroma")}


def reinitialize_vanna() -> dict:
    """Rebuild the Vanna service from current settings. Returns a status dict."""
    svc = get_vanna_service()
    llm = build_llm(get_llm_settings())
    if llm is None:
        return {"ready": False, "error": "No available LLM provider (check API keys / model)."}

    vs = get_vector_settings()
    vs_config = _vector_config_for(vs["store"], vs)
    ok = svc.initialize(llm, vs["store"], vs_config)
    if not ok:
        return {"ready": False, "error": svc.status().get("init_error")}

    db_url = get_db_settings()["source_db_url"]
    if db_url:
        try:
            svc.connect_db(db_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Vanna DB connect failed: {exc}")
    return svc.status()
