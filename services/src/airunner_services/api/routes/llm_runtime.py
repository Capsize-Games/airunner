"""Runtime plumbing helpers for runtime-backed LLM routes."""

from __future__ import annotations

import asyncio
from typing import Any, Iterable, List, Optional

from fastapi import HTTPException, Request, WebSocket

from airunner_services.ipc.messages import EnvelopeStatus, RequestEnvelope, StreamDelta
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import (
    ChatMessage as RuntimeChatMessage,
    LLMInvocationRequest,
    MessageRole,
    RuntimeAction,
    RuntimeKind,
    RuntimeMode,
)
from airunner_services.runtimes.registry import RuntimeRegistry

from .llm_contracts import ChatMessage


def get_runtime_registry(request: Request) -> Optional[RuntimeRegistry]:
    """Return the runtime registry attached to the FastAPI app."""
    return getattr(request.app.state, "runtime_registry", None)


def require_runtime_registry(request: Request) -> RuntimeRegistry:
    """Return the runtime registry or raise when it is unavailable."""
    runtime_registry = get_runtime_registry(request)
    if runtime_registry is None:
        raise HTTPException(status_code=503, detail="LLM runtime unavailable")
    return runtime_registry


def require_websocket_runtime_registry(websocket: WebSocket) -> RuntimeRegistry:
    """Return the runtime registry for a websocket session."""
    app = getattr(websocket, "app", None)
    state = getattr(app, "state", None)
    runtime_registry = getattr(state, "runtime_registry", None)
    if runtime_registry is None:
        raise HTTPException(status_code=503, detail="LLM runtime unavailable")
    return runtime_registry


def resolve_llm_client(registry: RuntimeRegistry) -> RuntimeClient:
    """Resolve the single local LLM runtime client."""
    try:
        return registry.resolve(RuntimeKind.LLM, provider="local")
    except KeyError as exc:
        raise HTTPException(status_code=503, detail="LLM runtime unavailable") from exc


def has_function_tool_data(
    messages: List[RuntimeChatMessage],
    tools: Optional[List[dict[str, Any]]] = None,
    tool_choice: Any = None,
) -> bool:
    """Whether this request uses the stateless function-tool contract."""
    return bool(tools or tool_choice is not None) or any(
        message.role is MessageRole.TOOL
        or bool(message.tool_calls)
        or message.tool_call_id is not None
        for message in messages
    )


def require_sidecar_for_function_tools(
    client: RuntimeClient,
    messages: List[RuntimeChatMessage],
    tools: Optional[List[dict[str, Any]]] = None,
    tool_choice: Any = None,
) -> None:
    """Prevent client schemas from entering local app-tool execution paths."""
    if not has_function_tool_data(messages, tools, tool_choice):
        return
    descriptor = getattr(client, "descriptor", None)
    if descriptor is None or descriptor.mode is not RuntimeMode.SIDECAR:
        raise HTTPException(
            status_code=501,
            detail="Function tools are unsupported by the configured LLM runtime",
        )


def to_runtime_messages(messages: List[ChatMessage]) -> List[RuntimeChatMessage]:
    """Convert API messages into the neutral runtime contract format."""
    runtime_messages = []
    for message in messages:
        try:
            role = MessageRole(message.role)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported chat role: {message.role}",
            ) from exc
        runtime_messages.append(
            RuntimeChatMessage(
                role=role,
                content=message.content,
                name=message.name,
                tool_calls=message.tool_calls,
                tool_call_id=message.tool_call_id,
            )
        )
    return runtime_messages


def runtime_error_status(response: Any) -> int:
    """Return the best HTTP status code for a runtime failure envelope."""
    error = getattr(response, "error", None)
    if error is not None and getattr(error, "code", "").endswith("_timeout"):
        return 504
    return 502


def raise_for_runtime_error(response: Any) -> None:
    """Raise an HTTP exception for a failed runtime response."""
    if response.status is EnvelopeStatus.SUCCEEDED:
        return
    detail = "LLM runtime request failed"
    if response.error is not None:
        detail = response.error.message
    raise HTTPException(
        status_code=runtime_error_status(response),
        detail=detail,
    )


async def invoke_llm_runtime(
    client: RuntimeClient,
    messages: List[RuntimeChatMessage],
    model: Optional[str],
    gguf_runtime_profile: Optional[str],
    temperature: float,
    max_tokens: Optional[int],
    enable_thinking: Optional[bool] = None,
    tools: Optional[List[dict[str, Any]]] = None,
    tool_choice: Any = None,
) -> tuple[str, str, List[dict[str, Any]], dict[str, Any]]:
    """Invoke the configured LLM runtime client.

    Returns ``(content, finish_reason, tool_calls, usage)``. The finish
    reason is the runtime's own value (``"length"`` when the token budget
    truncated the reply, e.g. a thinking model that spent it all reasoning),
    never a synthesized ``"stop"`` for a truncated empty answer.
    """
    invocation = LLMInvocationRequest(
        messages=messages,
        model=model,
        metadata={"gguf_runtime_profile": gguf_runtime_profile}
        if gguf_runtime_profile
        else {},
        temperature=temperature,
        max_tokens=max_tokens,
        enable_thinking=enable_thinking,
        tools=tools or [],
        tool_choice=tool_choice,
    )
    envelope = RequestEnvelope(
        runtime=RuntimeKind.LLM,
        action=RuntimeAction.INVOKE,
        provider="local",
        payload=invocation.model_dump(),
    )
    response = await asyncio.to_thread(client.invoke, envelope)
    raise_for_runtime_error(response)
    response_tools = response.payload.get("tools", [])
    response_usage = response.payload.get("usage", {})
    return (
        str(response.payload.get("content", "")),
        str(response.payload.get("finish_reason") or "stop"),
        response_tools if isinstance(response_tools, list) else [],
        response_usage if isinstance(response_usage, dict) else {},
    )


async def run_runtime_action(
    client: RuntimeClient,
    action: RuntimeAction,
) -> None:
    """Invoke a control action on the active LLM runtime."""
    response = await asyncio.to_thread(
        client.invoke,
        RequestEnvelope(
            runtime=RuntimeKind.LLM,
            action=action,
            provider="local",
        ),
    )
    raise_for_runtime_error(response)


async def next_stream_delta(iterator: Iterable[StreamDelta]) -> StreamDelta:
    """Read one runtime stream delta without blocking the event loop."""
    return await asyncio.to_thread(next, iterator)


async def stream_runtime(client: RuntimeClient, envelope: RequestEnvelope):
    """Yield runtime stream deltas from a blocking client iterator."""
    iterator = iter(client.stream(envelope))
    while True:
        try:
            yield await next_stream_delta(iterator)
        except StopIteration:
            return


def websocket_chunk(delta: StreamDelta) -> dict[str, Any]:
    """Convert a runtime stream delta into websocket payload shape."""
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
    payload = {
        "type": "chunk",
        "request_id": delta.request_id,
        "content": delta.delta.get("content", ""),
        "done": delta.final,
    }
    tool_calls = delta.delta.get("tool_calls")
    if tool_calls:
        payload["tool_calls"] = tool_calls
    if isinstance(delta.metadata.get("usage"), dict):
        payload["usage"] = delta.metadata["usage"]
    return payload


def websocket_envelope(
    data: dict[str, Any], request_id: str | None = None
) -> RequestEnvelope:
    """Build one streaming runtime envelope from a websocket payload."""
    profile = data.get("gguf_runtime_profile")
    payload = LLMInvocationRequest(
        model=data.get("model"),
        messages=[
            RuntimeChatMessage(
                role=MessageRole.USER,
                content=str(data.get("message", "")).strip(),
            )
        ],
        max_tokens=data.get("max_tokens"),
        metadata={"gguf_runtime_profile": profile} if profile else {},
        temperature=float(data.get("temperature", 0.7)),
        stream=True,
    )
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
