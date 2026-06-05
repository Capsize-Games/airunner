"""WebSocket endpoint for the TTS sidecar daemon.

Provides push-based messaging for TTS synthesis requests, replacing
HTTP request-response for the ``SidecarWebSocketTransport`` running
in the main API server process.

Protocol
--------
Same envelope format as the art daemon WebSocket (see
``art_daemon_ws.py``).

Request::
    {"request_id": "...", "action": "synthesize" | "load" | "unload" |
                                   "health",
     "payload": { ... }}

Progress push::
    {"type": "progress", "request_id": "...", "progress": 0-100,
     "phase": "processing", "status": "running"}

Final response::
    {"request_id": "...", "status": "succeeded"|"failed"|"cancelled",
     "payload": { ... }}
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from airunner_services.ipc.messages import EnvelopeStatus
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

router = APIRouter()


@router.websocket("/daemon/ws")
async def tts_daemon_websocket(websocket: WebSocket):
    """WebSocket endpoint for the TTS daemon sidecar transport."""
    await websocket.accept()
    logger.info("TTS daemon WebSocket connected")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "error": "Invalid JSON",
                })
                continue

            request_id = str(data.get("request_id", ""))
            action = str(data.get("action", "") or "")
            payload = data.get("payload", {})

            if action == "synthesize" or action == "invoke":
                await _handle_synthesize(websocket, request_id, payload)
            elif action == "load" or action == "load_model":
                await _handle_load(websocket, request_id, payload)
            elif action == "unload" or action == "unload_model":
                await _handle_unload(websocket, request_id)
            elif action == "health" or action == "status":
                await _handle_health(websocket, request_id)
            elif action == "cancel":
                await _handle_cancel(websocket, request_id, payload)
            else:
                await websocket.send_json({
                    "type": "response",
                    "request_id": request_id,
                    "status": "failed",
                    "error": f"Unknown action: {action}",
                })
    except WebSocketDisconnect:
        logger.info("TTS daemon WebSocket disconnected")
    except Exception as exc:
        logger.error("TTS daemon WebSocket error: %s", exc)
        try:
            await websocket.close()
        except Exception:
            pass


async def _handle_synthesize(
    websocket: WebSocket,
    request_id: str,
    payload: dict[str, Any],
) -> None:
    """Execute one TTS synthesis via the local runtime."""
    from fastapi import Request as FastAPIRequest

    from .tts_helpers import (
        build_tts_envelope,
        require_runtime_registry,
        resolve_tts_client,
    )
    from .tts_models import TTSRequest

    mock_request = FastAPIRequest({
        "type": "http",
        "app": getattr(websocket, "app", None),
    })

    try:
        client = resolve_tts_client(require_runtime_registry(mock_request))
    except Exception as exc:
        await websocket.send_json({
            "type": "response",
            "request_id": request_id,
            "status": "failed",
            "error": str(exc),
        })
        return

    # Build a TTS request from the payload
    tts_req = TTSRequest(
        text=str(payload.get("text", "")),
        voice=str(payload.get("voice", "")) or None,
        speed=float(payload.get("speed", 1.0)),
        model=str(payload.get("model")) if payload.get("model") else None,
    )

    # Push initial progress
    await websocket.send_json({
        "type": "progress",
        "request_id": request_id,
        "progress": 10.0,
        "phase": "synthesizing",
        "status": "running",
    })

    try:
        envelope = build_tts_envelope(tts_req)
        # Patch request_id to match our correlation
        envelope.request_id = request_id
        response = await asyncio.to_thread(client.invoke, envelope)
    except Exception as exc:
        await websocket.send_json({
            "type": "response",
            "request_id": request_id,
            "status": "failed",
            "error": str(exc),
        })
        return

    if response.status is not EnvelopeStatus.SUCCEEDED:
        error_msg = (
            response.error.message
            if response.error
            else "TTS synthesis failed"
        )
        await websocket.send_json({
            "type": "response",
            "request_id": request_id,
            "status": "failed",
            "error": error_msg,
        })
        return

    # Extract audio from response payload
    payload_data = response.payload or {}
    audio_b64 = (
        payload_data.get("audio_b64")
        or payload_data.get("audio")
        or ""
    )

    await websocket.send_json({
        "type": "progress",
        "request_id": request_id,
        "progress": 100.0,
        "phase": "complete",
        "status": "completed",
    })
    await websocket.send_json({
        "type": "response",
        "request_id": request_id,
        "status": "succeeded",
        "payload": {
            "accepted": True,
            "audio_b64": audio_b64,
        },
        "metadata": payload_data.get("metadata", {}),
    })


async def _handle_load(
    websocket: WebSocket,
    request_id: str,
    payload: dict[str, Any],
) -> None:
    """Load the TTS model (start the inner runtime)."""
    from fastapi import Request as FastAPIRequest

    from .tts_helpers import (
        require_runtime_registry,
        resolve_tts_client,
    )

    mock_request = FastAPIRequest({
        "type": "http",
        "app": getattr(websocket, "app", None),
    })

    try:
        client = resolve_tts_client(require_runtime_registry(mock_request))
        from airunner_services.runtimes.contracts import (  # noqa: PLC0415
            RuntimeAction, RuntimeKind,
        )
        from airunner_services.ipc.messages import RequestEnvelope  # noqa: PLC0415

        envelope = RequestEnvelope(
            request_id=request_id,
            runtime=RuntimeKind.TTS,
            action=RuntimeAction.LOAD_MODEL,
            payload=payload,
            metadata=payload.get("metadata", {}),
        )
        response = await asyncio.to_thread(client.invoke, envelope)
        status = "succeeded" if response.status is EnvelopeStatus.SUCCEEDED else "failed"
        await websocket.send_json({
            "type": "response",
            "request_id": request_id,
            "status": status,
            "payload": response.payload or {},
        })
    except Exception as exc:
        await websocket.send_json({
            "type": "response",
            "request_id": request_id,
            "status": "failed",
            "error": str(exc),
        })


async def _handle_unload(
    websocket: WebSocket,
    request_id: str,
) -> None:
    """Unload the TTS model."""
    from fastapi import Request as FastAPIRequest

    from .tts_helpers import (
        require_runtime_registry,
        resolve_tts_client,
    )

    mock_request = FastAPIRequest({
        "type": "http",
        "app": getattr(websocket, "app", None),
    })

    try:
        client = resolve_tts_client(require_runtime_registry(mock_request))
        from airunner_services.runtimes.contracts import (  # noqa: PLC0415
            RuntimeAction, RuntimeKind,
        )
        from airunner_services.ipc.messages import RequestEnvelope  # noqa: PLC0415

        envelope = RequestEnvelope(
            request_id=request_id,
            runtime=RuntimeKind.TTS,
            action=RuntimeAction.UNLOAD_MODEL,
        )
        response = await asyncio.to_thread(client.invoke, envelope)
        status = "succeeded" if response.status is EnvelopeStatus.SUCCEEDED else "failed"
        await websocket.send_json({
            "type": "response",
            "request_id": request_id,
            "status": status,
            "payload": response.payload or {},
        })
    except Exception as exc:
        await websocket.send_json({
            "type": "response",
            "request_id": request_id,
            "status": "failed",
            "error": str(exc),
        })


async def _handle_health(
    websocket: WebSocket,
    request_id: str,
) -> None:
    """Return the current TTS daemon health status."""
    from fastapi import Request as FastAPIRequest

    from .tts_helpers import (
        require_runtime_registry,
        resolve_tts_client,
    )

    mock_request = FastAPIRequest({
        "type": "http",
        "app": getattr(websocket, "app", None),
    })

    try:
        client = resolve_tts_client(require_runtime_registry(mock_request))
        health = client.healthcheck()
        await websocket.send_json({
            "type": "response",
            "request_id": request_id,
            "status": "succeeded",
            "payload": {
                "status": health.status.value,
                "details": health.details,
            },
            "metadata": health.metadata,
        })
    except Exception as exc:
        await websocket.send_json({
            "type": "response",
            "request_id": request_id,
            "status": "failed",
            "error": str(exc),
        })


async def _handle_cancel(
    websocket: WebSocket,
    request_id: str,
    payload: dict[str, Any],
) -> None:
    """Cancel an active TTS synthesis request."""
    from fastapi import Request as FastAPIRequest

    from .tts_helpers import (
        require_runtime_registry,
        resolve_tts_client,
    )

    mock_request = FastAPIRequest({
        "type": "http",
        "app": getattr(websocket, "app", None),
    })

    try:
        client = resolve_tts_client(require_runtime_registry(mock_request))
        cancel_request_id = str(
            payload.get("request_id") or payload.get("job_id") or request_id
        )
        response = await asyncio.to_thread(client.cancel, cancel_request_id)
        status = "cancelled" if response.status is EnvelopeStatus.CANCELLED else "failed"
        await websocket.send_json({
            "type": "response",
            "request_id": request_id,
            "status": status,
            "payload": response.payload or {},
        })
    except Exception as exc:
        await websocket.send_json({
            "type": "response",
            "request_id": request_id,
            "status": "failed",
            "error": str(exc),
        })
