"""Shared payload-building helpers for GGUF streaming."""

from __future__ import annotations

from typing import Any, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk

from airunner_services.llm.utils.stream_debug import print_stream_debug


def _base_stream_chat_kwargs(
    adapter: Any,
    converted_messages: list[dict[str, Any]],
    max_tokens: int,
) -> dict[str, Any]:
    """Build the common llama.cpp streaming payload."""
    return {
        "messages": converted_messages,
        "max_tokens": max_tokens,
        "temperature": adapter.temperature,
        "top_p": adapter.top_p,
        "top_k": adapter.top_k,
        "min_p": adapter.min_p,
        "repeat_penalty": adapter.repeat_penalty,
        "stream": True,
    }


def _apply_stop_sequences(
    chat_kwargs: dict[str, Any],
    stop: Optional[list[str]],
) -> None:
    """Attach stop sequences when the caller provided them."""
    if stop:
        chat_kwargs["stop"] = stop


def _apply_tool_calling_kwargs(
    adapter: Any,
    chat_kwargs: dict[str, Any],
) -> None:
    """Attach native tool-calling options when enabled."""
    if not adapter._use_native_tool_calling():
        return
    chat_kwargs["tools"] = adapter.tools
    if adapter.tool_choice is not None:
        chat_kwargs["tool_choice"] = adapter.tool_choice


def stream_chat_kwargs(
    adapter: Any,
    converted_messages: list[dict[str, Any]],
    max_tokens: int,
    stop: Optional[list[str]],
) -> dict[str, Any]:
    """Build one llama.cpp streaming chat kwargs payload."""
    chat_kwargs = _base_stream_chat_kwargs(
        adapter,
        converted_messages,
        max_tokens,
    )
    _apply_stop_sequences(chat_kwargs, stop)
    _apply_tool_calling_kwargs(adapter, chat_kwargs)
    return chat_kwargs


def _chunk_additional_kwargs(reasoning_text: Optional[str]) -> dict[str, Any]:
    """Return one message chunk's optional metadata payload."""
    if not reasoning_text:
        return {}
    return {"reasoning_content": reasoning_text}


def _build_text_generation_chunk(
    text: str,
    reasoning_text: Optional[str],
) -> ChatGenerationChunk:
    """Build one chat generation chunk for streamed text."""
    return ChatGenerationChunk(
        message=AIMessageChunk(
            content=text,
            additional_kwargs=_chunk_additional_kwargs(reasoning_text),
        )
    )


def _notify_run_manager(
    run_manager: Optional[CallbackManagerForLLMRun],
    text: str,
    chunk: ChatGenerationChunk,
) -> None:
    """Forward streamed tokens to the active callback manager."""
    if run_manager:
        run_manager.on_llm_new_token(text, chunk=chunk)


def text_chunk(
    text: str,
    reasoning_text: Optional[str],
    run_manager: Optional[CallbackManagerForLLMRun],
    chunk_index: int,
) -> ChatGenerationChunk:
    """Return one text chunk and notify the run manager when needed."""
    chunk = _build_text_generation_chunk(text, reasoning_text)
    print_stream_debug(
        "chat_gguf.yield",
        chunk_index=chunk_index,
        content=text,
        reasoning_content=reasoning_text,
    )
    _notify_run_manager(run_manager, text, chunk)
    return chunk