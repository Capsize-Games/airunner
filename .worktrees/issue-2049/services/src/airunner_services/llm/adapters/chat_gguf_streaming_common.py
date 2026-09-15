"""Shared streaming helpers for ChatGGUF."""

from __future__ import annotations

from typing import Any, Optional

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
        buffer = _tool_call_buffer(tool_call_buffers, raw_call)
        _merge_native_tool_call(buffer, raw_call)


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


def _tool_call_buffer(
    tool_call_buffers: dict[int, dict[str, Any]],
    raw_call: dict[str, Any],
) -> dict[str, Any]:
    """Return the mutable buffer used for one streamed tool call."""
    index = raw_call.get("index", len(tool_call_buffers))
    return tool_call_buffers.setdefault(
        index,
        {
            "id": None,
            "type": "function",
            "function": {"name": "", "arguments": ""},
        },
    )


def _merge_native_tool_call(
    buffer: dict[str, Any],
    raw_call: dict[str, Any],
) -> None:
    """Merge one streamed tool-call delta into its buffer."""
    if raw_call.get("id"):
        buffer["id"] = raw_call["id"]
    if raw_call.get("type"):
        buffer["type"] = raw_call["type"]
    function = raw_call.get("function") or {}
    _merge_function_delta(buffer, function, "name")
    _merge_function_delta(buffer, function, "arguments")


def _merge_function_delta(
    buffer: dict[str, Any],
    function: dict[str, Any],
    key: str,
) -> None:
    """Merge one streamed function field into the active tool buffer."""
    fragment = function.get(key)
    if not fragment:
        return
    buffer["function"][key] = merge_streamed_text(
        buffer["function"][key],
        fragment,
    )
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