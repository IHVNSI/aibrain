"""LLM provider abstraction.

Each provider exposes a uniform `.chat(messages) -> str` where `messages` is a
list of {"role": "system"|"user"|"assistant", "content": str}. This lets the
Vanna service and the conversation rewriter use any backend interchangeably:
free offline Hugging Face, or cloud OpenAI / Gemini / Anthropic (Claude).
"""
import logging
import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    name: str = "base"
    model: str = ""

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Return the assistant text for the given chat messages."""
        raise NotImplementedError

    def available(self) -> bool:
        return True


# --------------------------------------------------------------------------- #
# Cloud: OpenAI
# --------------------------------------------------------------------------- #
class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", temperature: float = 0.0):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self._client = None
        self.last_usage: Dict[str, Any] = {}

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def available(self) -> bool:
        return bool(self.api_key)

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        client = self._get_client()
        resp = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
        )
        usage = getattr(resp, "usage", None)
        self.last_usage = {
            "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
            "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        return resp.choices[0].message.content or ""


# --------------------------------------------------------------------------- #
# Cloud: Gemini (Google)
# --------------------------------------------------------------------------- #
class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash", temperature: float = 0.0):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self._model_obj = None
        self.last_usage: Dict[str, Any] = {}

    def available(self) -> bool:
        return bool(self.api_key)

    def _to_gemini(self, messages: List[Dict[str, str]]):
        """Convert chat messages to (system_instruction, contents)."""
        system = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
        contents = []
        for m in messages:
            role = m.get("role")
            if role == "system":
                continue
            g_role = "user" if role == "user" else "model"
            contents.append({"role": g_role, "parts": [{"text": m.get("content", "")}]})
        return system, contents

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        system, contents = self._to_gemini(messages)
        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system or None,
        )
        resp = model.generate_content(
            contents,
            generation_config={"temperature": kwargs.get("temperature", self.temperature)},
        )
        usage = getattr(resp, "usage_metadata", None)
        self.last_usage = {
            "input_tokens": getattr(usage, "prompt_token_count", 0) or 0,
            "output_tokens": getattr(usage, "candidates_token_count", 0) or 0,
            "cache_creation_input_tokens": getattr(usage, "cached_content_token_count", 0) or 0,
            "cache_read_input_tokens": 0,
        }
        return (getattr(resp, "text", "") or "").strip()


# --------------------------------------------------------------------------- #
# Cloud: Anthropic (Claude) — with prompt caching on the system prefix
# --------------------------------------------------------------------------- #
class ClaudeProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6", temperature: float = 0.0,
                 max_tokens: int = 2048):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None
        self.last_usage: Dict[str, Any] = {}

    def available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        client = self._get_client()
        # Split system messages out; cache the (stable) system prefix.
        system_text = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
        convo = [m for m in messages if m.get("role") in ("user", "assistant")]
        system_blocks = None
        if system_text:
            system_blocks = [{
                "type": "text",
                "text": system_text,
                "cache_control": {"type": "ephemeral"},
            }]
        resp = client.messages.create(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            temperature=kwargs.get("temperature", self.temperature),
            system=system_blocks,
            messages=[{"role": m["role"], "content": m["content"]} for m in convo] or
                     [{"role": "user", "content": " "}],
        )
        try:
            self.last_usage = {
                "input_tokens": getattr(resp.usage, "input_tokens", 0),
                "output_tokens": getattr(resp.usage, "output_tokens", 0),
                "cache_creation_input_tokens": getattr(resp.usage, "cache_creation_input_tokens", 0),
                "cache_read_input_tokens": getattr(resp.usage, "cache_read_input_tokens", 0),
            }
        except Exception:
            self.last_usage = {}
        parts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
        return "".join(parts).strip()


# --------------------------------------------------------------------------- #
# Free offline: Hugging Face (transformers) — seq2seq or causal
# --------------------------------------------------------------------------- #
class HuggingFaceProvider(LLMProvider):
    name = "huggingface"

    def __init__(self, model: str = "google/flan-t5-base", max_new_tokens: int = 512):
        self.model = model
        self.max_new_tokens = max_new_tokens
        self._tok = None
        self._model = None
        self._is_seq2seq = False
        self._load_error = None
        self.last_usage: Dict[str, Any] = {}

    def available(self) -> bool:
        return self._ensure_loaded()

    def _ensure_loaded(self) -> bool:
        if self._model is not None:
            return True
        if self._load_error is not None:
            return False
        try:
            from transformers import (
                AutoTokenizer,
                AutoModelForSeq2SeqLM,
                AutoModelForCausalLM,
                AutoConfig,
            )
            cfg = AutoConfig.from_pretrained(self.model)
            self._is_seq2seq = bool(getattr(cfg, "is_encoder_decoder", False))
            self._tok = AutoTokenizer.from_pretrained(self.model)
            loader = AutoModelForSeq2SeqLM if self._is_seq2seq else AutoModelForCausalLM
            self._model = loader.from_pretrained(self.model)
            self._model.eval()
            logger.info(f"✅ Hugging Face LLM loaded: {self.model} (seq2seq={self._is_seq2seq})")
            return True
        except Exception as exc:  # noqa: BLE001
            self._load_error = f"{type(exc).__name__}: {exc}"
            logger.warning(f"⚠️  Hugging Face LLM unavailable: {self._load_error}")
            return False

    @staticmethod
    def _flatten(messages: List[Dict[str, str]]) -> str:
        lines = []
        for m in messages:
            role = m.get("role", "user").upper()
            lines.append(f"{role}: {m.get('content','')}")
        lines.append("ASSISTANT:")
        return "\n".join(lines)

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        if not self._ensure_loaded():
            raise RuntimeError(f"Hugging Face model not available: {self._load_error}")
        import torch
        prompt = self._flatten(messages)
        inputs = self._tok(prompt, return_tensors="pt", truncation=True, max_length=2048)
        input_tokens = int(inputs["input_ids"].shape[-1]) if "input_ids" in inputs else 0
        with torch.no_grad():
            out = self._model.generate(
                **inputs,
                max_new_tokens=kwargs.get("max_new_tokens", self.max_new_tokens),
                num_beams=4,
                early_stopping=True,
            )
        output_tokens = int(out.shape[-1]) if hasattr(out, "shape") else 0
        self.last_usage = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        if self._is_seq2seq:
            return self._tok.decode(out[0], skip_special_tokens=True).strip()
        # Causal models echo the prompt — strip it.
        full = self._tok.decode(out[0], skip_special_tokens=True)
        return full[len(prompt):].strip() if full.startswith(prompt) else full.strip()
