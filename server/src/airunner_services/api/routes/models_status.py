"""Model status SSE endpoint and active-model management routes.

Provides a real-time stream of ``MODEL_STATUS_CHANGED_SIGNAL`` events
so that the frontend can show loaded/loading models and allow users to
unload individual models.
"""

from __future__ import annotations

import json
import asyncio
import logging
import queue
import threading
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from airunner_services.contract_enums import SignalCode
from airunner_services.model_management import ModelResourceManager
from airunner_services.runtimes.contracts import RuntimeAction
from airunner_services.utils.application.signal_mediator import (
    SignalMediator,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Module-level SSE state for model status events
_status_subscribers: list[queue.Queue[bytes]] = []
_status_lock = threading.Lock()

# In-memory snapshot of externally-tracked models (e.g. embedding).
# Keyed by model_id, value is a dict with keys:
#   model_id, model_type, status, can_unload, vram_gb, ram_gb
_external_models: dict[str, dict] = {}
_external_models_lock = threading.Lock()


# ── Data models ─────────────────────────────────────────────────────


class ActiveModelResponse(BaseModel):
    """One active model entry exposed to the frontend."""

    model_id: str = Field(..., description="Unique model identifier")
    model_type: str = Field(
        ...,
        description="Model category (embedding, llm, etc.)",
    )
    status: str = Field(
        ...,
        description="Current lifecycle status",
    )
    can_unload: bool = Field(
        default=False,
        description="Whether the client may unload this model",
    )
    vram_gb: float = Field(default=0.0)
    ram_gb: float = Field(default=0.0)
    name: str = Field(
        default="",
        description="Human-readable model name (filename without path)",
    )


class ActiveModelsResponse(BaseModel):
    """Wrapper returned by the active-models endpoint."""

    models: list[ActiveModelResponse] = Field(default_factory=list)


class UnloadModelRequest(BaseModel):
    """Payload for the unload-model endpoint."""

    model_id: str = Field(..., description="Model identifier to unload")
    model_type: str = Field(
        default="",
        description="Optional category hint",
    )


# ── SSE helpers ──────────────────────────────────────────────────────


def _notify_status_subscribers(
    data: dict[str, Any],
) -> None:
    """Push one model-status event to every connected SSE subscriber."""
    line = b"data: " + json.dumps(data).encode("utf-8") + b"\n\n"
    with _status_lock:
        dead: list[queue.Queue[bytes]] = []
        for q in _status_subscribers:
            try:
                q.put_nowait(line)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _status_subscribers.remove(q)


# ── SSE endpoint ─────────────────────────────────────────────────────


@router.get("/models/status")
def watch_model_status() -> StreamingResponse:
    """SSE stream that emits model-lifecycle status changes.

    Events:
      ``{"type": "model_status", "model_type": "...", "model_id": "...",
        "status": "loaded|loading|unloaded"}``
    """
    q: queue.Queue[bytes] = queue.Queue(maxsize=128)

    with _status_lock:
        _status_subscribers.append(q)

    def _cleanup() -> None:
        with _status_lock:
            if q in _status_subscribers:
                _status_subscribers.remove(q)

    def event_stream():  # noqa: DOC502
        try:
            while True:
                try:
                    data = q.get(timeout=30)
                    yield data
                except queue.Empty:
                    yield b": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            _cleanup()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── REST endpoints ───────────────────────────────────────────────────


@router.get("/models/active", response_model=ActiveModelsResponse)
async def list_active_models() -> ActiveModelsResponse:
    """Return all models currently tracked as active (not unloaded).

    Merges models tracked by ``ModelResourceManager`` (art, LLM) with
    externally-tracked models such as the embedding model.
    """
    result: list[ActiveModelResponse] = []

    # Read from ModelResourceManager
    try:
        resource_mgr = ModelResourceManager()
        for m in resource_mgr.get_active_models():
            result.append(
                ActiveModelResponse(
                    model_id=m.model_id,
                    model_type=m.model_type,
                    status=m.state.value,
                    can_unload=m.can_unload,
                    vram_gb=m.vram_allocated_gb,
                    ram_gb=m.ram_allocated_gb,
                    name=m.name,
                )
            )
    except Exception as exc:
        logger.warning("Failed to read active models: %s", exc)

    # Merge externally-tracked models (embedding, etc.)
    with _external_models_lock:
        seen_ids = {r.model_id for r in result}
        for ext in _external_models.values():
            if ext["model_id"] not in seen_ids:
                result.append(
                    ActiveModelResponse(
                        model_id=ext["model_id"],
                        model_type=ext["model_type"],
                        status=ext["status"],
                        can_unload=ext["can_unload"],
                        vram_gb=ext.get("vram_gb", 0.0),
                        ram_gb=ext.get("ram_gb", 0.0),
                        name=ext.get("name", ""),
                    )
                )

    return ActiveModelsResponse(models=result)


@router.post("/models/unload")
async def unload_model(
    request: UnloadModelRequest,
    req: Request,
) -> dict[str, str]:
    """Request one model to be unloaded.

    For embedding models, triggers unload via the signal mediator.
    The agent's ``on_rag_index_cancel_signal`` handler will set the
    interrupt flag, and on the next progress check the agent will call
    ``unload_rag()`` and emit a status-update signal.
    """
    model_type_lower = (
        request.model_type.strip().lower()
        or request.model_id.strip().lower()
    )

    if "embedding" in model_type_lower:
        SignalMediator().emit_signal(
            SignalCode.RAG_INDEX_CANCEL,
            {"unload_embedding": True},
        )
        logger.info("Unload requested for embedding model %s", request.model_id)
        return {
            "status": "accepted",
            "message": "Embedding model unload requested",
        }

    if "llm" in model_type_lower:
        SignalMediator().emit_signal(
            SignalCode.LLM_UNLOAD_SIGNAL,
            {},
        )
        logger.info("Unload requested for LLM model %s", request.model_id)
        return {
            "status": "accepted",
            "message": "LLM unload requested",
        }

    if any(
        keyword in model_type_lower
        for keyword in ("art", "sd", "stablediffusion", "z-image", "turbo")
    ):
        from .art_runtime_control import (  # noqa: PLC0415
            build_control_request,
            control_response,
        )
        from .art_runtime_registry import (  # noqa: PLC0415
            require_runtime_registry,
            resolve_art_client,
        )

        # Fire unload in the background so the HTTP response returns
        # immediately instead of blocking on the worker thread.
        async def _fire_art_unload():
            try:
                client = resolve_art_client(
                    require_runtime_registry(req),
                )
                envelope = build_control_request(
                    RuntimeAction.UNLOAD_MODEL, None, None,
                )
                await asyncio.to_thread(client.invoke, envelope)
            except Exception as exc:
                logger.warning(
                    "Background art unload failed: %s", exc,
                )

        asyncio.create_task(_fire_art_unload())

        logger.info(
            "Unload requested for art model %s (type=%s)",
            request.model_id,
            request.model_type,
        )
        return {
            "status": "accepted",
            "message": "Art model unload requested",
        }

    logger.info(
        "Unload requested for model %s (type=%s) – no handler",
        request.model_id,
        request.model_type,
    )
    return {"status": "accepted", "message": f"No handler for {request.model_type}"}


# ── Signal registration (called from server.py) ──────────────────────


def _register_model_status_handlers(app_instance) -> None:
    """Bridge ``MODEL_STATUS_CHANGED_SIGNAL`` to the SSE subscriber list.

    Tries ``app_instance.mediator`` first, then the global
    ``SignalMediator`` singleton.
    """
    signal_mediator = getattr(app_instance, "mediator", None)
    if signal_mediator is None:
        signal_mediator = SignalMediator()
        logger.info(
            "Fell back to global SignalMediator for model-status SSE",
        )

    from airunner_services.contract_enums import SignalCode  # noqa: PLC0415

    def on_model_status(data: dict) -> None:
        model_type = str(data.get("model", data.get("model_type", "")))
        model_id = str(
            data.get("path", data.get("model_id", model_type)),
        )
        status = str(data.get("status", ""))

        # Keep the external-models dict in sync for the REST endpoint
        with _external_models_lock:
            if status in ("unloaded", "failed"):
                _external_models.pop(model_id, None)
            elif status == "loading":
                _external_models[model_id] = {
                    "model_id": model_id,
                    "model_type": model_type,
                    "status": "loading",
                    "can_unload": False,
                    "vram_gb": 0.0,
                    "ram_gb": 0.0,
                }
            elif status == "loaded":
                _external_models[model_id] = {
                    "model_id": model_id,
                    "model_type": model_type,
                    "status": "loaded",
                    "can_unload": True,
                    "vram_gb": 0.0,
                    "ram_gb": 0.0,
                }

        payload: dict[str, Any] = {
            "type": "model_status",
            "model_type": model_type,
            "model_id": model_id,
            "status": status,
        }
        _notify_status_subscribers(payload)

    try:
        signal_mediator.register(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            on_model_status,
        )
        logger.info("Registered model-status SSE bridge handler")
    except Exception as exc:
        logger.warning(
            "Failed to register model-status SSE handler: %s",
            exc,
        )
