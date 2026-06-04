"""GGUF chat-format detection helpers."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional


@lru_cache(maxsize=16)
def _llama_chat_format_supported(name: str) -> bool:
    """Return True when the runtime supports a chat format."""
    if not name:
        return False
    try:
        from llama_cpp import llama_chat_format

        llama_chat_format.get_chat_completion_handler(name)
    except Exception:
        return False
    return True


def _detect_chat_format(model_path: str) -> Optional[str]:
    """Detect the appropriate chat format based on model filename."""
    path_lower = model_path.lower()
    if "gpt-oss" in path_lower:
        if _llama_chat_format_supported("gpt-oss"):
            return "gpt-oss"
        return None
    if "qwen" in path_lower:
        return "chatml"
    if any(name in path_lower for name in ["llama-3", "llama3", "meta-llama-3"]):
        return "llama-3"
    if any(name in path_lower for name in ["mistral", "magistral"]):
        return "mistral-instruct"
    return None