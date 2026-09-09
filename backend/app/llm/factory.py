"""LLM factory — builds the active provider from saved settings or env config."""
import logging
from typing import Optional

from ..config import Config
from ..models import Setting
from .providers import (
    LLMProvider,
    OpenAIProvider,
    GeminiProvider,
    ClaudeProvider,
    HuggingFaceProvider,
)

logger = logging.getLogger(__name__)


def get_llm_settings() -> dict:
    """Resolve effective LLM settings: DB override first, then env defaults."""
    saved = Setting.get("llm_config") or {}
    return {
        "provider": saved.get("provider", Config.LLM_PROVIDER),
        "model": saved.get("model", Config.LLM_MODEL),
        "gemini_api_key": saved.get("gemini_api_key") or Config.GEMINI_API_KEY,
        "openai_api_key": saved.get("openai_api_key") or Config.OPENAI_API_KEY,
        "anthropic_api_key": saved.get("anthropic_api_key") or Config.ANTHROPIC_API_KEY,
        "hf_model": saved.get("hf_model", Config.HF_MODEL),
        "temperature": float(saved.get("temperature", 0.0)),
    }


def build_llm(settings: Optional[dict] = None) -> Optional[LLMProvider]:
    """Instantiate the configured LLM provider. Returns None if unavailable."""
    s = settings or get_llm_settings()
    provider = (s.get("provider") or "gemini").lower()
    temperature = s.get("temperature", 0.0)

    try:
        if provider == "openai":
            llm = OpenAIProvider(s["openai_api_key"], s.get("model") or "gpt-4o-mini", temperature)
        elif provider in ("gemini", "google"):
            llm = GeminiProvider(s["gemini_api_key"], s.get("model") or "gemini-2.0-flash", temperature)
        elif provider in ("anthropic", "claude"):
            llm = ClaudeProvider(s["anthropic_api_key"], s.get("model") or "claude-sonnet-4-6", temperature)
        elif provider in ("huggingface", "hf"):
            llm = HuggingFaceProvider(s.get("hf_model") or Config.HF_MODEL, Config.HF_MAX_NEW_TOKENS)
        else:
            logger.warning(f"Unknown LLM provider '{provider}', defaulting to Gemini")
            llm = GeminiProvider(s["gemini_api_key"], "gemini-2.0-flash", temperature)

        if not llm.available():
            logger.warning(f"LLM provider '{provider}' is not available (missing key/model).")
            return None
        logger.info(f"✅ Active LLM provider: {llm.name} ({llm.model})")
        return llm
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to build LLM '{provider}': {exc}")
        return None
