"""HF chat-template helpers for GGUF runtime loading."""

from __future__ import annotations

import os
from typing import Any

from airunner_services.llm.provider_config import LLMProviderConfig

try:
    from llama_cpp import llama_chat_format
except ImportError:
    llama_chat_format = None

try:
    from transformers import AutoTokenizer
except ImportError:
    AutoTokenizer = None


def configure_chat_handler(adapter: Any) -> None:
    """Install one HF chat-template handler when the model needs it."""
    if getattr(adapter, "_llama", None) is None:
        return
    repo_id = chat_template_repo_id(adapter)
    if not repo_id:
        return
    base_handler = build_hf_chat_handler(adapter, repo_id)
    if base_handler is None:
        return

    def chat_handler_with_kwargs(*args: Any, **kwargs: Any) -> Any:
        template_kwargs = {
            "enable_thinking": bool(getattr(adapter, "enable_thinking", True))
        }
        return base_handler(*args, **{**template_kwargs, **kwargs})

    adapter._llama.chat_handler = chat_handler_with_kwargs
    adapter.logger.info("Using HF chat template handler for %s", repo_id)


def chat_template_repo_id(adapter: Any) -> str | None:
    """Return the HF repo id for one thinking-capable local GGUF model."""
    model_name = os.path.basename(str(adapter.model_path or ""))
    model_id = LLMProviderConfig.resolve_model_id("local", model_name)
    if not model_id:
        return None
    model_info = LLMProviderConfig.get_model_info("local", model_id)
    if not model_info.get("supports_thinking"):
        return None
    repo_id = str(model_info.get("repo_id") or "").strip()
    if "qwen" not in repo_id.lower():
        return None
    return repo_id or None


def build_hf_chat_handler(adapter: Any, repo_id: str) -> Any | None:
    """Build one llama.cpp chat handler from an HF tokenizer template."""
    if AutoTokenizer is None or llama_chat_format is None:
        return None
    tokenizer = load_chat_template_tokenizer(adapter, repo_id)
    if tokenizer is None:
        return None
    return llama_chat_format.chat_formatter_to_chat_completion_handler(
        _format_messages_handler(tokenizer)
    )


def _format_messages_handler(tokenizer: Any) -> Any:
    """Return a llama.cpp formatter callback for one HF tokenizer."""

    def format_messages(messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        return _chat_formatter_response(tokenizer, messages, kwargs)

    return format_messages


def _chat_formatter_response(
    tokenizer: Any,
    messages: list[dict[str, Any]],
    kwargs: dict[str, Any],
) -> Any:
    """Return one llama.cpp chat formatter response from an HF tokenizer."""
    tokenizer.use_default_system_prompt = False
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        **kwargs,
    )
    return llama_chat_format.ChatFormatterResponse(
        prompt=prompt,
        stop=str(tokenizer.eos_token or ""),
        added_special=True,
    )


def load_chat_template_tokenizer(
    adapter: Any,
    repo_id: str,
) -> Any | None:
    """Load one HF tokenizer, preferring cache before network."""
    tokenizer = _cached_chat_template_tokenizer(repo_id)
    if tokenizer is not None:
        return tokenizer
    adapter.logger.info(
        "HF tokenizer cache missing for %s; downloading chat template "
        "assets",
        repo_id,
    )
    return _download_chat_template_tokenizer(adapter, repo_id)


def _cached_chat_template_tokenizer(repo_id: str) -> Any | None:
    """Return a locally cached HF tokenizer when available."""
    try:
        return AutoTokenizer.from_pretrained(
            repo_id,
            local_files_only=True,
            use_fast=False,
        )
    except Exception:
        return None


def _download_chat_template_tokenizer(
    adapter: Any,
    repo_id: str,
) -> Any | None:
    """Download one HF tokenizer after cache lookup misses."""
    try:
        return AutoTokenizer.from_pretrained(
            repo_id,
            use_fast=False,
        )
    except Exception as exc:
        adapter.logger.warning(
            "Unable to load HF tokenizer for %s: %s",
            repo_id,
            exc,
        )
        return None
