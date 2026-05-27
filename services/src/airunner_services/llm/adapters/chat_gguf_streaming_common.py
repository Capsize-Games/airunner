"""Shared streaming helpers for ChatGGUF."""

from __future__ import annotations

from typing import Any, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk

from airunner_services.llm.utils.stream_debug import print_stream_debug


def merge_streamed_text(existing: str, fragment: str) -> str:
    """Merge one streamed text fragment without duplicating overlap."""
    if not existing or not fragment:
        return existing + fragment
    if fragment == existing or existing.endswith(fragment):
        return existing
    if fragment.startswith(existing):
        return fragment
    max_overlap = min(len(existing), len(fragment))
    for overlap in range(max_overlap, 0, -1):
        if existing.endswith(fragment[:overlap]):
            return existing + fragment[overlap:]
    return existing + fragment


def merge_native_tool_call_deltas(
    adapter: Any,
    tool_call_buffers: dict[int, dict[str, Any]],
    raw_tool_calls: Optional[list[dict[str, Any]]],
) -> None:
    """Merge streamed native tool call deltas into one buffer map."""
    for raw_call in raw_tool_calls or []:
        index = raw_call.get("index", len(tool_call_buffers))
        buffer = tool_call_buffers.setdefault(
            index,
            {
                "id": None,
                "type": "function",
                "function": {"name": "", "arguments": ""},
            },
        )
        if raw_call.get("id"):
            buffer["id"] = raw_call["id"]
        if raw_call.get("type"):
            buffer["type"] = raw_call["type"]
        function = raw_call.get("function") or {}
        if function.get("name"):
            buffer["function"]["name"] = merge_streamed_text(
                buffer["function"]["name"],
                function["name"],
            )
        if function.get("arguments"):
            buffer["function"]["arguments"] = merge_streamed_text(
                buffer["function"]["arguments"],
                function["arguments"],
            )


def finalize_native_tool_call_deltas(
    adapter: Any,
    tool_call_buffers: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert buffered streamed tool call deltas into normalized calls."""
    if not tool_call_buffers:
        return []
    ordered_calls = [
        tool_call_buffers[index] for index in sorted(tool_call_buffers)
    ]
    return adapter._parse_native_tool_calls(ordered_calls)


def _stream_chat_kwargs(
    adapter: Any,
    converted_messages: list[dict[str, Any]],
    max_tokens: int,
    stop: Optional[list[str]],
) -> dict[str, Any]:
    """Build one llama.cpp streaming chat kwargs payload."""
    chat_kwargs = {
        "messages": converted_messages,
        "max_tokens": max_tokens,
        "temperature": adapter.temperature,
        "top_p": adapter.top_p,
        "top_k": adapter.top_k,
        "min_p": adapter.min_p,
        "repeat_penalty": adapter.repeat_penalty,
        "stream": True,
    }
    if stop:
        chat_kwargs["stop"] = stop
    if adapter._use_native_tool_calling():
        chat_kwargs["tools"] = adapter.tools
        if adapter.tool_choice is not None:
            chat_kwargs["tool_choice"] = adapter.tool_choice
    return chat_kwargs


def _log_stream_start(adapter: Any, max_tokens: int) -> None:
    """Log the start of one streaming llama.cpp request."""
    adapter.logger.info(
        "[ChatGGUF._stream] Calling create_chat_completion with "
        "max_tokens=%s",
        max_tokens,
    )
    adapter.logger.info(
        "[ChatGGUF._stream] Number of tools bound: %s",
        len(adapter.tools) if adapter.tools else 0,
    )
    adapter.logger.info(
        "[ChatGGUF._stream] tool_choice: %s",
        adapter.tool_choice,
    )


def _log_stream_delta(chunk_index: int, delta: dict[str, Any]) -> None:
    """Log one streaming delta through the shared debug helper."""
    print_stream_debug(
        "chat_gguf.delta",
        chunk_index=chunk_index,
        content=delta.get("content"),
        reasoning_content=delta.get("reasoning_content"),
        tool_calls=delta.get("tool_calls"),
    )


def _text_chunk(
    text: str,
    reasoning_text: Optional[str],
    run_manager: Optional[CallbackManagerForLLMRun],
    chunk_index: int,
) -> ChatGenerationChunk:
    """Return one text chunk and notify the run manager when needed."""
    additional_kwargs = {}
    if reasoning_text:
        additional_kwargs["reasoning_content"] = reasoning_text
    chunk = ChatGenerationChunk(
        message=AIMessageChunk(
            content=text,
            additional_kwargs=additional_kwargs,
        )
    )
    print_stream_debug(
        "chat_gguf.yield",
        chunk_index=chunk_index,
        content=text,
        reasoning_content=reasoning_text,
    )
    if run_manager:
        run_manager.on_llm_new_token(text, chunk=chunk)
    return chunk