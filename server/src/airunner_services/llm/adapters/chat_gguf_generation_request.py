"""Request-building helpers for GGUF chat generation."""

from __future__ import annotations

import time
from typing import Any, Optional

from langchain_core.outputs import ChatGeneration, ChatResult

from airunner_services.llm.adapters.chat_gguf_streaming_payloads import (
    _apply_thinking_kwargs,
)


def generate_raw_gpt_oss_result(
    adapter: Any,
    messages: list[Any],
    stop: Optional[list[str]],
    effective_max_tokens: Any,
) -> ChatResult:
    """Generate one raw Harmony completion result."""
    del effective_max_tokens
    completion_kwargs = _raw_completion_kwargs(adapter, messages, stop)
    raw_text = _raw_completion_text(adapter, completion_kwargs)
    message = adapter._build_gpt_oss_message_from_raw(raw_text)
    return ChatResult(generations=[ChatGeneration(message=message)])


def _raw_completion_kwargs(
    adapter: Any,
    messages: list[Any],
    stop: Optional[list[str]],
) -> dict[str, Any]:
    """Return kwargs for one raw GPT-OSS completion call."""
    return adapter._build_gpt_oss_completion_kwargs(
        messages,
        stop,
        stream=False,
    )


def _raw_completion_text(
    adapter: Any,
    completion_kwargs: dict[str, Any],
) -> str:
    """Run one raw GPT-OSS completion request and return the text."""
    call_started = time.perf_counter()
    response = adapter._llama.create_completion(**completion_kwargs)
    adapter.logger.info(
        "[ChatGGUF._generate] create_completion returned in %.3fs",
        time.perf_counter() - call_started,
    )
    raw_text = response["choices"][0].get("text", "") or ""
    return adapter._continue_prefilled_gpt_oss_tool_call(
        completion_kwargs,
        raw_text,
    )


def chat_completion_kwargs(
    adapter: Any,
    converted_messages: list[dict[str, Any]],
    stop: Optional[list[str]],
    effective_max_tokens: Any,
) -> dict[str, Any]:
    """Build one llama.cpp chat completion kwargs payload."""
    max_tokens = effective_max_tokens(adapter, adapter.max_tokens)
    chat_kwargs = _base_chat_kwargs(adapter, converted_messages, max_tokens)
    if stop:
        chat_kwargs["stop"] = stop
    _apply_native_tool_kwargs(adapter, chat_kwargs)
    _apply_thinking_kwargs(adapter, chat_kwargs)
    return chat_kwargs


def _base_chat_kwargs(
    adapter: Any,
    converted_messages: list[dict[str, Any]],
    max_tokens: Optional[int],
) -> dict[str, Any]:
    """Return the base llama.cpp chat completion kwargs payload."""
    return {
        "messages": converted_messages,
        "max_tokens": max_tokens,
        "temperature": adapter.temperature,
        "top_p": adapter.top_p,
        "top_k": adapter.top_k,
        "min_p": adapter.min_p,
        "repeat_penalty": adapter.repeat_penalty,
        "stream": False,
    }


def _apply_native_tool_kwargs(
    adapter: Any,
    chat_kwargs: dict[str, Any],
) -> None:
    """Apply native tool-calling kwargs when the adapter supports them."""
    if not adapter._use_native_tool_calling():
        return
    chat_kwargs["tools"] = adapter.tools
    if adapter.tool_choice is not None:
        chat_kwargs["tool_choice"] = adapter.tool_choice
