"""Client-shaped chat envelope for ``/api/v1/llm/stream`` (#2230).

The UwUChat web client sends ``{"type": "chat", "messages": [...]}`` and
reads ``chunk`` / ``error`` frames — see ``airunnerweb``
``client/src/features/llm/useLLMWebSocket.ts`` and ``wsMessageHandler.ts``.
The legacy desktop envelope on the same socket is a flat
``{"message": "..."}`` shape validated by
:class:`~airunner_services.api.routes.llm_contracts.LLMStreamMessage`.

Both request shapes share one socket and are disambiguated by ``type``,
so the legacy path is untouched: a frame without ``type == "chat"`` is
never routed here. Replies use the client's own vocabulary, not a
translation of the legacy one.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, WebSocket
from pydantic import ValidationError

from airunner_services.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import (
    ChatMessage as RuntimeChatMessage,
    LLMInvocationRequest,
    MessageRole,
    RuntimeAction,
    RuntimeKind,
)

from .llm_contracts import max_ws_message_chars, max_ws_output_tokens
from .llm_runtime import require_sidecar_for_function_tools, stream_runtime

_CHAT_TYPE = "chat"


class ClientChatError(ValueError):
    """A structurally valid client chat frame outside configured bounds."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def is_client_chat(data: Dict[str, Any]) -> bool:
    """Return True when a frame is the client's ``chat`` envelope."""
    return data.get("type") == _CHAT_TYPE


def _role(raw: Any) -> MessageRole:
    try:
        return MessageRole(str(raw))
    except ValueError as exc:
        raise ClientChatError("unsupported_role") from exc


def _one_message(raw: Any, total: int) -> RuntimeChatMessage:
    if not isinstance(raw, dict):
        raise ClientChatError("bad_message")
    raw_content = raw.get("content")
    if raw_content is None and raw.get("tool_calls"):
        content = None
    else:
        content = str(raw_content if raw_content is not None else "")
    if total + len(content or "") > max_ws_message_chars():
        raise ClientChatError("message_too_long")
    try:
        return RuntimeChatMessage(
            role=_role(raw.get("role")),
            content=content,
            name=raw.get("name"),
            tool_calls=raw.get("tool_calls") or [],
            tool_call_id=raw.get("tool_call_id"),
        )
    except ValidationError as exc:
        raise ClientChatError("invalid_tool_message") from exc


def parse_client_chat(data: Dict[str, Any]) -> List[RuntimeChatMessage]:
    """Validate a client ``chat`` frame into runtime messages."""
    raw_messages = data.get("messages")
    if not isinstance(raw_messages, list) or not raw_messages:
        raise ClientChatError("empty_messages")
    messages: List[RuntimeChatMessage] = []
    total = 0
    for raw in raw_messages:
        message = _one_message(raw, total)
        total += len(message.content or "")
        messages.append(message)
    return messages


def _max_tokens(data: Dict[str, Any]) -> Optional[int]:
    value = data.get("max_tokens")
    if value is None:
        return max_ws_output_tokens()
    try:
        tokens = int(value)
    except (TypeError, ValueError) as exc:
        raise ClientChatError("max_tokens_out_of_bounds") from exc
    if not 1 <= tokens <= max_ws_output_tokens():
        raise ClientChatError("max_tokens_out_of_bounds")
    return tokens


def _temperature(data: Dict[str, Any]) -> float:
    try:
        value = float(data.get("temperature", 0.7))
    except (TypeError, ValueError) as exc:
        raise ClientChatError("temperature_out_of_bounds") from exc
    if not 0.0 <= value <= 2.0:
        raise ClientChatError("temperature_out_of_bounds")
    return value


def client_envelope(
    messages: List[RuntimeChatMessage],
    data: Dict[str, Any],
    request_id: str | None = None,
) -> RequestEnvelope:
    """Build one streaming runtime envelope from a client chat frame."""
    try:
        payload = LLMInvocationRequest(
            model=data.get("model"),
            messages=messages,
            max_tokens=_max_tokens(data),
            temperature=_temperature(data),
            stream=True,
            tools=data.get("tools", []),
            tool_choice=data.get("tool_choice"),
        )
    except ValidationError as exc:
        raise ClientChatError("invalid_tool_request") from exc
    envelope_values = {
        "runtime": RuntimeKind.LLM,
        "action": RuntimeAction.INVOKE,
        "provider": "local",
        "stream": True,
        "payload": payload.model_dump(),
    }
    if request_id is not None:
        envelope_values["request_id"] = request_id
    return RequestEnvelope(**envelope_values)


def client_frame(delta: Any, call_chain_id: Optional[str]) -> Dict[str, Any]:
    """Map one runtime delta onto the client's ``chunk``/``error`` shape."""
    if delta.status is EnvelopeStatus.FAILED:
        return {
            "type": "error",
            "request_id": delta.request_id,
            "content": delta.metadata.get("error", "LLM runtime failed"),
            "done": True,
        }
    if delta.status is EnvelopeStatus.CANCELLED:
        return {
            "type": "cancelled",
            "request_id": delta.request_id,
            "done": True,
        }
    frame: Dict[str, Any] = {
        "type": "chunk",
        "request_id": delta.request_id,
        "content": delta.delta.get("content", ""),
        "done": delta.final,
    }
    tool_calls = delta.delta.get("tool_calls")
    if tool_calls:
        frame["tool_calls"] = tool_calls
    usage = delta.metadata.get("usage")
    if isinstance(usage, dict):
        frame["usage"] = usage
    if delta.final and call_chain_id:
        frame["call_chain_id"] = call_chain_id
    return frame


async def stream_client_chat(
    websocket: WebSocket,
    client: RuntimeClient,
    data: Dict[str, Any],
    request_id: str | None = None,
    owner: Any | None = None,
    pending_events: list[dict] | None = None,
) -> None:
    """Stream one client chat frame as client-shaped frames."""
    try:
        messages = parse_client_chat(data)
        require_sidecar_for_function_tools(
            client, messages, data.get("tools", []), data.get("tool_choice")
        )
        envelope = client_envelope(messages, data, request_id)
    except HTTPException:
        await websocket.send_json(
            {"type": "error", "content": "unsupported_tool_runtime", "done": True}
        )
        return
    except ClientChatError as exc:
        await websocket.send_json(
            {"type": "error", "content": exc.code, "done": True}
        )
        return
    call_chain_id = str(data.get("conversation_id") or "") or None
    if owner is None or request_id is None:
        async for delta in stream_runtime(client, envelope):
            await websocket.send_json(client_frame(delta, call_chain_id))
            if delta.final:
                break
        return
    from .llm_request_registry import stream_owned_request

    await stream_owned_request(
        websocket,
        client,
        envelope,
        request_id,
        owner,
        lambda delta: client_frame(delta, call_chain_id),
        pending_events if pending_events is not None else [],
    )
