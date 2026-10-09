"""GUI chunk vocabulary for companion turns (B13).

Pure builders mapping B01 ``CompanionStreamEvent`` values onto the
daemon-chunk-shaped dicts the Qt chat stream already consumes, plus
the reverse mapping onto ``LLMResponse`` fields and tool-status
payloads. Qt-free: the chat widget performs the final signal emit.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .contracts import (
    CallChainId,
    CompanionErrorCode,
    CompanionStreamEvent,
)

TEXT_SIGNAL = "llm_text_streamed"
TOOL_STATUS_SIGNAL = "llm_tool_status"


def base_chunk(
    request_id: Optional[str],
    conversation_id: Optional[int],
    call_chain_id: Optional[CallChainId],
    sequence: int,
) -> Dict[str, Any]:
    """Return one chunk carrying a turn's preserved IDs."""
    return {
        "request_id": request_id,
        "conversation_id": conversation_id,
        "call_chain_id": (
            None if call_chain_id is None else str(call_chain_id)
        ),
        "sequence_number": sequence,
    }


def _ids(
    event: CompanionStreamEvent,
    request_id: Optional[str],
    conversation_id: Optional[int],
) -> Dict[str, Any]:
    """Return one event chunk's preserved-ID prefix."""
    return base_chunk(
        request_id,
        conversation_id,
        event.call_chain_id,
        event.sequence,
    )


def text_chunk(
    event: CompanionStreamEvent,
    request_id: Optional[str],
    conversation_id: Optional[int],
    is_first: bool,
) -> Dict[str, Any]:
    """Return one visible assistant chunk for a text event."""
    chunk = {
        **_ids(event, request_id, conversation_id),
        "message": event.delta_text,
        "message_type": "assistant",
        "is_first_message": is_first,
        "is_end_of_message": event.final,
    }
    names = [
        tool_name(call) for call in event.tool_calls if isinstance(call, dict)
    ]
    if names:
        chunk["tools"] = names
    return chunk


def tool_status_chunks(
    event: CompanionStreamEvent,
    request_id: Optional[str],
    conversation_id: Optional[int],
) -> List[Dict[str, Any]]:
    """Return one tool-status chunk per tool call in an event."""
    chunks = []
    for index, call in enumerate(event.tool_calls):
        record = call if isinstance(call, dict) else {}
        name = tool_name(record)
        arguments = tool_arguments_text(record)
        chunks.append(
            {
                **_ids(event, request_id, conversation_id),
                "message_type": "tool_status",
                "tool_id": tool_id(
                    record,
                    event.call_chain_id,
                    event.sequence,
                    index,
                ),
                "tool_name": name,
                "query": arguments or name,
                "status": "completed" if event.final else "running",
                "details": arguments,
            }
        )
    return chunks


def error_chunk(
    event: CompanionStreamEvent,
    error: CompanionErrorCode,
    request_id: Optional[str],
    conversation_id: Optional[int],
    is_first: bool,
) -> Dict[str, Any]:
    """Return the terminal chunk surfacing a failed turn."""
    return {
        **_ids(event, request_id, conversation_id),
        "error": True,
        "error_code": error.code,
        "retryable": error.retryable,
        "message": error_text(error),
        "is_first_message": is_first,
        "is_end_of_message": True,
    }


def cancelled_chunk(
    call_chain_id: CallChainId,
    sequence: int,
    request_id: Optional[str],
    conversation_id: Optional[int],
    is_first: bool,
) -> Dict[str, Any]:
    """Return the silent terminal chunk settling a cancelled turn.

    Mirrors the stop button: the stream settles with no visible
    message rather than narrating the cancel.
    """
    return {
        **base_chunk(request_id, conversation_id, call_chain_id, sequence),
        "message": "",
        "message_type": "assistant",
        "cancelled": True,
        "is_first_message": is_first,
        "is_end_of_message": True,
    }


def chunk_signal(chunk: Dict[str, Any]) -> str:
    """Return which GUI signal one adapter chunk routes to."""
    if chunk.get("message_type") == "tool_status":
        return TOOL_STATUS_SIGNAL
    return TEXT_SIGNAL


def chunk_to_response_fields(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """Map one text chunk onto ``LLMResponse`` constructor fields.

    Mirrors ``_response_from_daemon_chunk`` in ``LLMAPIService``;
    the caller supplies ``action``/``node_id`` from its context.
    """
    usage = chunk.get("usage") or {}
    return {
        "message": chunk.get("message", "") or "",
        "is_first_message": bool(chunk.get("is_first_message")),
        "is_end_of_message": bool(chunk.get("is_end_of_message")),
        "sequence_number": int(chunk.get("sequence_number") or 0),
        "request_id": chunk.get("request_id"),
        "tools": chunk.get("tools") or chunk.get("tool_calls"),
        "is_system_message": bool(chunk.get("error", False)),
        "message_type": chunk.get("message_type"),
        "thinking_content": chunk.get("thinking_content"),
        "tool_name": chunk.get("tool_name"),
        "tool_arguments": chunk.get("tool_arguments"),
        "tool_status": chunk.get("tool_status"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }


def chunk_to_tool_status_payload(chunk: Dict[str, Any]) -> Dict[str, Any]:
    """Map one tool-status chunk onto the tool-status signal payload.

    Mirrors ``_forward_structured_tool_status_chunk`` in
    ``LLMAPIService``.
    """
    return {
        "tool_id": chunk.get("tool_id") or "",
        "tool_name": chunk.get("tool_name") or "",
        "query": chunk.get("query") or "",
        "status": chunk.get("status") or "",
        "details": chunk.get("details") or "",
        "conversation_id": chunk.get("conversation_id"),
        "request_id": chunk.get("request_id"),
        "metadata": chunk.get("metadata"),
        "timestamp": chunk.get("timestamp"),
    }


def error_text(error: CompanionErrorCode) -> str:
    """Return the user-safe text surfacing one companion error."""
    text = f"Error: {error.detail or error.code}"
    if error.retryable:
        text += " (retryable)"
    return text


def tool_name(call: Dict[str, Any]) -> str:
    """Return one tool call's display name, defensively."""
    name = call.get("name") or call.get("tool_name")
    if not name:
        function = call.get("function") or {}
        if isinstance(function, dict):
            name = function.get("name")
    return str(name) if name else "tool"


def tool_id(
    call: Dict[str, Any],
    call_chain_id: CallChainId,
    sequence: int,
    index: int,
) -> str:
    """Return one tool call's stable status-widget id."""
    raw = call.get("id") or call.get("tool_id")
    if raw:
        return str(raw)
    return f"{call_chain_id}-{sequence}-{index}"


def tool_arguments_text(call: Dict[str, Any]) -> str:
    """Return one tool call's arguments as deterministic text."""
    arguments = call.get("arguments")
    if arguments is None:
        arguments = call.get("query", call.get("input", ""))
    if isinstance(arguments, dict):
        return json.dumps(arguments, sort_keys=True)
    return str(arguments or "")


__all__ = [
    "TEXT_SIGNAL",
    "TOOL_STATUS_SIGNAL",
    "base_chunk",
    "cancelled_chunk",
    "chunk_signal",
    "chunk_to_response_fields",
    "chunk_to_tool_status_payload",
    "error_chunk",
    "error_text",
    "text_chunk",
    "tool_arguments_text",
    "tool_id",
    "tool_name",
    "tool_status_chunks",
]
