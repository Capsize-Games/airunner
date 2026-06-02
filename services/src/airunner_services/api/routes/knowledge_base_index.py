"""RAG document indexing endpoint with SSE progress streaming."""

from __future__ import annotations

import json
import logging
import queue
import threading
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from airunner_services.api.routes.legacy_common import get_airunner_app
from airunner_services.contract_enums import SignalCode
from airunner_services.utils.application.signal_mediator import SignalMediator

router = APIRouter()
logger = logging.getLogger(__name__)

# Module-level SSE state for indexing progress
_index_subscribers: list[queue.Queue[bytes]] = []
_index_lock = threading.Lock()


def _resolve_emit_signal(app: Any):
    """Resolve ``emit_signal`` from an app instance.

    Tries, in order:
      1. ``app.emit_signal`` directly
      2. ``app.mediator.emit_signal`` (``MediatorMixin`` property)
      3. The global ``SignalMediator`` singleton
    """
    emit_signal = getattr(app, "emit_signal", None)
    if callable(emit_signal):
        return emit_signal

    mediator = getattr(app, "mediator", None)
    if mediator is not None:
        mediator_emit = getattr(mediator, "emit_signal", None)
        if callable(mediator_emit):
            return mediator_emit

    return SignalMediator().emit_signal


@router.post("/documents/index-all")
async def index_all_documents(request: Request):
    """Trigger indexing of all documents via the app signal system."""
    app = get_airunner_app(request)
    emit_signal = _resolve_emit_signal(app)

    if emit_signal is None:
        raise HTTPException(
            status_code=503,
            detail="Indexing is not available (no signal system)",
        )

    emit_signal(
        SignalCode.RAG_INDEX_ALL_DOCUMENTS,
        {},
    )

    return {"status": "started", "message": "Document indexing triggered"}


@router.post("/documents/index-cancel")
async def cancel_indexing(request: Request):
    """Cancel an in-progress indexing operation."""
    app = get_airunner_app(request)
    emit_signal = _resolve_emit_signal(app)

    if emit_signal:
        emit_signal(SignalCode.RAG_INDEX_CANCEL, {})

    return {"status": "cancelled"}


def _notify_index_subscribers(data: dict[str, Any]) -> None:
    """Push one progress event to every connected SSE subscriber."""
    line = b"data: " + json.dumps(data).encode("utf-8") + b"\n\n"
    with _index_lock:
        dead: list[queue.Queue[bytes]] = []
        for q in _index_subscribers:
            try:
                q.put_nowait(line)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _index_subscribers.remove(q)


@router.get("/documents/index-progress")
def watch_index_progress():
    """SSE stream that emits indexing progress events.

    Events:
      ``{"type": "progress", "current": N, "total": M}``
      ``{"type": "complete", "success": true, "message": "..."}``
      ``{"type": "error", "message": "..."}``
    """
    q: queue.Queue[bytes] = queue.Queue(maxsize=128)

    with _index_lock:
        _index_subscribers.append(q)

    def _cleanup():
        with _index_lock:
            if q in _index_subscribers:
                _index_subscribers.remove(q)

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


def _register_signal_handlers(app_instance) -> None:
    """Register signal handlers on one app instance to bridge to SSE.

    Tries ``app_instance.mediator`` first (``MediatorMixin`` attribute),
    then falls back to the global ``SignalMediator`` singleton.
    """
    from airunner_services.utils.application.signal_mediator import (  # noqa: PLC0415
        SignalMediator,
    )

    signal_mediator = getattr(app_instance, "mediator", None)
    if signal_mediator is None:
        signal_mediator = SignalMediator()
        logger.info(
            "Fell back to global SignalMediator singleton for SSE bridge",
        )

    def on_progress(data: dict) -> None:
        _notify_index_subscribers({
            "type": "progress",
            "current": int(data.get("current", 0)),
            "total": int(data.get("total", 0)),
            "message": str(data.get("message", "")),
            "document_name": str(
                data.get("document_name", data.get("documentName", "")),
            ),
        })

    def on_complete(data: dict) -> None:
        _notify_index_subscribers({
            "type": "complete",
            "success": bool(data.get("success", False)),
            "message": str(data.get("message", "")),
        })

    def on_error(data: dict) -> None:
        _notify_index_subscribers({
            "type": "error",
            "message": str(data.get("message", "")),
        })

    # Register handlers on the signal mediator
    try:
        signal_mediator.register(
            SignalCode.RAG_INDEXING_PROGRESS, on_progress,
        )
        signal_mediator.register(
            SignalCode.RAG_INDEXING_COMPLETE, on_complete,
        )
        logger.info(
            "Registered indexing progress SSE bridge handlers",
        )
    except Exception as exc:
        logger.warning(
            "Failed to register indexing SSE handlers: %s", exc,
        )
