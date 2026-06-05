"""WebSocket endpoint for the Art sidecar daemon.

Protocol: request_id-correlated envelopes over WS.
See ``tts_daemon_ws.py`` for more details.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from airunner_services.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

router = APIRouter()


async def _resolve_art_client(ws: WebSocket):
    """Resolve the art runtime client from the WS app state."""
    from fastapi import Request as FastAPIRequest
    from airunner_services.api.routes.art_runtime_registry import (
        require_runtime_registry,
        resolve_art_client,
    )
    mock = FastAPIRequest({"type": "http"})
    mock.app = getattr(ws, "app", None)
    return resolve_art_client(require_runtime_registry(mock))


@router.websocket("/daemon/ws")
async def art_daemon_websocket(websocket: WebSocket):
    await websocket.accept()
    logger.info("Art daemon WebSocket connected")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "error": "Invalid JSON"})
                continue

            rid = str(data.get("request_id", ""))
            action = str(data.get("action", "") or "")
            payload = data.get("payload", {})

            if action in ("generate", "invoke"):
                await _handle_generate(websocket, rid, payload)
            elif action == "cancel":
                await _handle_cancel(websocket, rid, payload)
            elif action in ("status", "health"):
                await _handle_health(websocket, rid)
            elif action in ("unload", "unload_model"):
                await _handle_unload(websocket, rid)
            else:
                await websocket.send_json({
                    "type": "response", "request_id": rid,
                    "status": "failed", "error": f"Unknown action: {action}",
                })
    except WebSocketDisconnect:
        logger.info("Art daemon WebSocket disconnected")
    except Exception as exc:
        logger.error("Art daemon WebSocket error: %s", exc)


async def _handle_generate(
    ws: WebSocket, request_id: str, payload: dict[str, Any],
) -> None:
    try:
        client = await _resolve_art_client(ws)
    except Exception as exc:
        await ws.send_json({"type": "response", "request_id": request_id, "status": "failed", "error": str(exc)})
        return

    envelope = RequestEnvelope(
        request_id=request_id, runtime=RuntimeKind.ART,
        action=RuntimeAction.INVOKE, payload=payload,
        metadata=payload.get("metadata", {}),
    )
    await ws.send_json({"type": "progress", "request_id": request_id, "progress": 5.0, "phase": "loading", "status": "running"})
    try:
        response = await asyncio.to_thread(client.invoke, envelope)
    except Exception as exc:
        await ws.send_json({"type": "response", "request_id": request_id, "status": "failed", "error": str(exc)})
        return
    if response.status is not EnvelopeStatus.SUCCEEDED:
        await ws.send_json({"type": "response", "request_id": request_id, "status": "failed", "error": response.error.message if response.error else "Art generation failed"})
        return
    await ws.send_json({"type": "progress", "request_id": request_id, "progress": 100.0, "phase": "complete", "status": "completed"})
    await ws.send_json({"type": "response", "request_id": request_id, "status": "succeeded", "payload": response.payload or {}, "metadata": response.payload.get("metadata", {}) if response.payload else {}})


async def _handle_cancel(
    ws: WebSocket, request_id: str, payload: dict[str, Any],
) -> None:
    try:
        client = await _resolve_art_client(ws)
        cid = str(payload.get("request_id") or payload.get("job_id") or request_id)
        response = await asyncio.to_thread(client.cancel, cid)
        status = "cancelled" if response.status is EnvelopeStatus.CANCELLED else "failed"
        await ws.send_json({"type": "response", "request_id": request_id, "status": status, "payload": response.payload or {}})
    except Exception as exc:
        await ws.send_json({"type": "response", "request_id": request_id, "status": "failed", "error": str(exc)})


async def _handle_health(ws: WebSocket, request_id: str) -> None:
    try:
        client = await _resolve_art_client(ws)
        health = client.healthcheck()
        await ws.send_json({"type": "response", "request_id": request_id, "status": "succeeded", "payload": {"status": health.status.value, "details": health.details}, "metadata": health.metadata})
    except Exception as exc:
        await ws.send_json({"type": "response", "request_id": request_id, "status": "failed", "error": str(exc)})


async def _handle_unload(ws: WebSocket, request_id: str) -> None:
    try:
        client = await _resolve_art_client(ws)
        envelope = RequestEnvelope(request_id=request_id, runtime=RuntimeKind.ART, action=RuntimeAction.UNLOAD_MODEL)
        response = await asyncio.to_thread(client.invoke, envelope)
        status = "succeeded" if response.status is EnvelopeStatus.SUCCEEDED else "failed"
        await ws.send_json({"type": "response", "request_id": request_id, "status": status, "payload": response.payload or {}})
    except Exception as exc:
        await ws.send_json({"type": "response", "request_id": request_id, "status": "failed", "error": str(exc)})
