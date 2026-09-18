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

from fastapi import WebSocket

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
from .llm_runtime import stream_runtime

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
    content = str(raw.get("content", ""))
    if total + len(content) > max_ws_message_chars():
        raise ClientChatError("message_too_long")
    return RuntimeChatMessage(role=_role(raw.get("role")), content=content)


def parse_client_chat(data: Dict[str, Any]) -> List[RuntimeChatMessage]:
    """Validate a client ``chat`` frame into runtime messages."""
    raw_messages = data.get("messages")
    if not isinstance(raw_messages, list) or not raw_messages:
        raise ClientChatError("empty_messages")
    messages: List[RuntimeChatMessage] = []
    total = 0
    for raw in raw_messages:
        message = _one_message(raw, total)
        total += len(message.content)
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
    messages: List[RuntimeChatMessage], data: Dict[str, Any]
) -> RequestEnvelope:
    """Build one streaming runtime envelope from a client chat frame."""
    payload = LLMInvocationRequest(
        model=data.get("model"),
        messages=messages,
        max_tokens=_max_tokens(data),
        temperature=_temperature(data),
        stream=True,
    )
    return RequestEnvelope(
        runtime=RuntimeKind.LLM,
        action=RuntimeAction.INVOKE,
        provider="local",
        stream=True,
        payload=payload.model_dump(),
    )


def client_frame(delta: Any, call_chain_id: Optional[str]) -> Dict[str, Any]:
    """Map one runtime delta onto the client's ``chunk``/``error`` shape."""
    if delta.status is EnvelopeStatus.FAILED:
        return {
            "type": "error",
            "content": delta.metadata.get("error", "LLM runtime failed"),
            "done": True,
        }
    frame: Dict[str, Any] = {
        "type": "chunk",
        "content": delta.delta.get("content", ""),
        "done": delta.final,
    }
    if delta.final and call_chain_id:
        frame["call_chain_id"] = call_chain_id
    return frame


async def stream_client_chat(
    websocket: WebSocket,
    client: RuntimeClient,
    data: Dict[str, Any],
) -> None:
    """Stream one client chat frame as client-shaped frames."""
    try:
        envelope = client_envelope(parse_client_chat(data), data)
    except ClientChatError as exc:
        await websocket.send_json(
            {"type": "error", "content": exc.code, "done": True}
        )
        return
    call_chain_id = str(data.get("conversation_id") or "") or None
    async for delta in stream_runtime(client, envelope):
        await websocket.send_json(client_frame(delta, call_chain_id))
        if delta.final:
            break
