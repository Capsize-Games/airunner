"""LLM API routes backed by the runtime registry."""

from __future__ import annotations

import asyncio
from typing import Any, Iterable, List, Optional

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel

from airunner.components.llm.config.provider_config import LLMProviderConfig
from airunner.components.llm.data.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner.components.model_management.model_registry import ModelRegistry
from airunner.components.settings.data.path_settings import PathSettings
from airunner.ipc.messages import EnvelopeStatus, RequestEnvelope, StreamDelta
from airunner.runtimes.base import RuntimeClient
from airunner.runtimes.contracts import (
    ChatMessage as RuntimeChatMessage,
    LLMInvocationRequest,
    MessageRole,
    RuntimeAction,
    RuntimeKind,
)
from airunner.runtimes.registry import RuntimeRegistry
from airunner.settings import AIRUNNER_BASE_PATH, AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

router = APIRouter()


class ChatMessage(BaseModel):
    """Chat message submitted to the HTTP API."""

    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    """Chat completion request."""

    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False


class ChatCompletionResponse(BaseModel):
    """Chat completion response."""

    content: str
    model: str
    finish_reason: str


class CompletionRequest(BaseModel):
    """Text completion request."""

    prompt: str
    max_tokens: int = 100
    temperature: float = 0.7


class CompletionResponse(BaseModel):
    """Text completion response."""

    text: str
    finish_reason: str


class ModelInfo(BaseModel):
    """LLM model information."""

    id: str
    name: str
    loaded: bool
    size_mb: Optional[int] = None


class ModelLoadRequest(BaseModel):
    """Model load request."""

    model_id: str


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


def _to_runtime_messages(
    messages: List[ChatMessage],
) -> List[RuntimeChatMessage]:
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
            RuntimeChatMessage(role=role, content=message.content)
        )
    return runtime_messages


def _selected_model_id(settings: Any) -> str:
    """Return the configured local model id when one can be resolved."""
    if settings is None:
        return ""

    for value in (
        getattr(settings, "model_id", None),
        getattr(settings, "model_version", None),
        getattr(settings, "model_path", None),
    ):
        if not value:
            continue
        resolved = LLMProviderConfig.resolve_model_id("local", str(value))
        if resolved:
            return resolved
    return ""


def _persist_model_selection(model_id: str) -> str:
    """Persist the selected local model in the existing settings tables."""
    settings = LLMGeneratorSettings.objects.first()
    if settings is None:
        raise HTTPException(status_code=503, detail="LLM settings unavailable")

    resolved_id = LLMProviderConfig.resolve_model_id("local", model_id)
    if not resolved_id:
        raise HTTPException(status_code=404, detail="LLM model not found")

    path_settings = PathSettings.objects.first()
    base_path = getattr(path_settings, "base_path", AIRUNNER_BASE_PATH)
    settings.model_id = resolved_id
    settings.model_version = resolved_id
    settings.model_path = LLMProviderConfig.get_local_storage_path(
        base_path,
        "local",
        model_id=resolved_id,
    )
    settings.save()
    return resolved_id


def _runtime_error_status(response: Any) -> int:
    """Return the best HTTP status code for a runtime failure envelope."""
    error = getattr(response, "error", None)
    if error is not None and getattr(error, "code", "").endswith("_timeout"):
        return 504
    return 502


def _raise_for_runtime_error(response: Any) -> None:
    """Raise an HTTP exception for a failed runtime response."""
    if response.status is EnvelopeStatus.SUCCEEDED:
        return
    detail = "LLM runtime request failed"
    if response.error is not None:
        detail = response.error.message
    raise HTTPException(
        status_code=_runtime_error_status(response),
        detail=detail,
    )


async def _invoke_llm_runtime(
    client: RuntimeClient,
    messages: List[RuntimeChatMessage],
    model: Optional[str],
    temperature: float,
    max_tokens: Optional[int],
) -> str:
    """Invoke the configured LLM runtime client."""
    invocation = LLMInvocationRequest(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    envelope = RequestEnvelope(
        runtime=RuntimeKind.LLM,
        action=RuntimeAction.INVOKE,
        provider="local",
        payload=invocation.model_dump(),
    )
    response = await asyncio.to_thread(client.invoke, envelope)
    _raise_for_runtime_error(response)
    return str(response.payload.get("content", ""))


async def _run_runtime_action(
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
    _raise_for_runtime_error(response)


async def _next_stream_delta(iterator: Iterable[StreamDelta]) -> StreamDelta:
    """Read one runtime stream delta without blocking the event loop."""
    return await asyncio.to_thread(next, iterator)


async def _stream_runtime(
    client: RuntimeClient,
    envelope: RequestEnvelope,
):
    """Yield runtime stream deltas from a blocking client iterator."""
    iterator = iter(client.stream(envelope))
    while True:
        try:
            yield await _next_stream_delta(iterator)
        except StopIteration:
            return


def _websocket_chunk(delta: StreamDelta) -> dict[str, Any]:
    """Convert a runtime stream delta into websocket payload shape."""
    if delta.status is EnvelopeStatus.FAILED:
        return {
            "type": "error",
            "content": delta.metadata.get("error", "LLM runtime failed"),
            "done": True,
        }

    payload = {
        "type": "chunk",
        "content": delta.delta.get("content", ""),
        "done": delta.final,
    }
    tool_calls = delta.delta.get("tool_calls")
    if tool_calls:
        payload["tool_calls"] = tool_calls
    return payload


@router.post("/chat", response_model=ChatCompletionResponse)
async def chat_completion(request: ChatCompletionRequest, req: Request):
    """Run chat completion against the runtime-backed local LLM."""
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    client = resolve_llm_client(require_runtime_registry(req))
    response = await _invoke_llm_runtime(
        client,
        _to_runtime_messages(request.messages),
        request.model,
        request.temperature,
        request.max_tokens,
    )
    return ChatCompletionResponse(
        content=response,
        model=request.model or "default",
        finish_reason="stop",
    )


@router.post("/completion", response_model=CompletionResponse)
async def text_completion(request: CompletionRequest, req: Request):
    """Run text completion against the runtime-backed local LLM."""
    client = resolve_llm_client(require_runtime_registry(req))
    response = await _invoke_llm_runtime(
        client,
        [RuntimeChatMessage(role=MessageRole.USER, content=request.prompt)],
        None,
        request.temperature,
        request.max_tokens,
    )
    return CompletionResponse(text=response, finish_reason="stop")


@router.get("/models", response_model=List[ModelInfo])
async def list_models(_req: Request):
    """List available local LLM models."""
    settings = LLMGeneratorSettings.objects.first()
    current_model_id = _selected_model_id(settings)

    try:
        registry = ModelRegistry()
        models = []
        for model_id, model_spec in registry.models.items():
            if model_spec.model_type.value != "llm":
                continue
            models.append(
                ModelInfo(
                    id=model_id,
                    name=model_spec.name,
                    loaded=(model_id == current_model_id),
                    size_mb=model_spec.size_mb,
                )
            )
        return models
    except Exception as exc:
        logger.error(f"Error listing models: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing models: {str(exc)}",
        ) from exc


@router.post("/load")
async def load_model(request: ModelLoadRequest, req: Request):
    """Persist the selected model and load it through the runtime boundary."""
    resolved_id = _persist_model_selection(request.model_id)
    client = resolve_llm_client(require_runtime_registry(req))
    await _run_runtime_action(client, RuntimeAction.LOAD_MODEL)
    return {"status": "success", "model": resolved_id}


@router.post("/unload")
async def unload_model(req: Request):
    """Unload the active local LLM through the runtime boundary."""
    client = resolve_llm_client(require_runtime_registry(req))
    await _run_runtime_action(client, RuntimeAction.UNLOAD_MODEL)
    return {"status": "success"}


@router.websocket("/stream")
async def websocket_chat(websocket: WebSocket):
    """Stream chat responses from the runtime-backed local LLM."""
    await websocket.accept()

    try:
        client = resolve_llm_client(require_websocket_runtime_registry(websocket))
        while True:
            data = await websocket.receive_json()
            prompt = str(data.get("message", "")).strip()
            if not prompt:
                await websocket.send_json(
                    {"type": "error", "content": "No message provided"}
                )
                continue

            envelope = RequestEnvelope(
                runtime=RuntimeKind.LLM,
                action=RuntimeAction.INVOKE,
                provider="local",
                stream=True,
                payload=LLMInvocationRequest(
                    model=data.get("model"),
                    messages=[
                        RuntimeChatMessage(
                            role=MessageRole.USER,
                            content=prompt,
                        )
                    ],
                    max_tokens=data.get("max_tokens"),
                    temperature=float(data.get("temperature", 0.7)),
                    stream=True,
                ).model_dump(),
            )

            async for delta in _stream_runtime(client, envelope):
                await websocket.send_json(_websocket_chunk(delta))
                if delta.final:
                    break

    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except HTTPException as exc:
        await websocket.send_json(
            {"type": "error", "content": exc.detail, "done": True}
        )
    except Exception as exc:
        logger.error(f"WebSocket error: {exc}")
        await websocket.send_json(
            {
                "type": "error",
                "content": f"Server error: {str(exc)}",
                "done": True,
            }
        )
