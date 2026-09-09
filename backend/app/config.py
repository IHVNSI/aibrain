"""Application configuration loaded from environment variables."""
import os
from dotenv import load_dotenv

# Load .env from the backend directory
_BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(_BASE_DIR, ".env"))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    PORT = int(os.getenv("PORT", "5001"))

    # Admin DB (settings, conversations, audit, training metadata)
    ADMIN_DB_URL = os.getenv("ADMIN_DB_URL", "sqlite:///assistantai.db")

    # Source DB to run generated SQL against
    SOURCE_DB_URL = os.getenv("SOURCE_DB_URL", "")

    # Default LLM
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
    LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

    # Hugging Face offline LLM
    HF_MODEL = os.getenv("HF_MODEL", "google/flan-t5-base")
    HF_MAX_NEW_TOKENS = int(os.getenv("HF_MAX_NEW_TOKENS", "512"))

    # Vector store
    VECTOR_STORE = os.getenv("VECTOR_STORE", "chromadb")
    CHROMA_PATH = os.getenv("CHROMA_PATH", "./vanna_chroma")
    FAISS_PATH = os.getenv("FAISS_PATH", "./vanna_faiss")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX = os.getenv("PINECONE_INDEX", "assistantai")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "")

    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
