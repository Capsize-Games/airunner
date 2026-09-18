"""WebSocket text-to-speech route for the desktop chat client.

The chat surface keeps one persistent socket per feature rather than
re-issuing HTTP requests, so TTS has its own ``/api/v1/tts/ws`` in
addition to ``POST /api/v1/tts/synthesize``. The wire contract is fixed
by the client:

* client -> ``{"type": "synthesize", "text", "voice", "speed"}``
* server -> ``{"type": "audio", "data": "<base64 WAV>"}``
* server -> ``{"type": "error", "message": "<reason>"}``

Audio is base64 in a JSON frame because the client decodes it through
``atob`` and wraps the bytes in a ``Blob``; there is no binary framing.
"""

from __future__ import annotations

import asyncio
import base64
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from airunner_services.ipc.messages import EnvelopeStatus
from airunner_common.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.utils.application.log_hygiene import summarize_text

from .tts_helpers import (
    build_tts_envelope,
    require_runtime_registry,
    resolve_tts_client,
    tts_error_status_code,
    tts_response_audio,
)
from .tts_models import TTSRequest
from .ws_auth import websocket_auth_failed

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
router = APIRouter()


async def _synthesize(ws: WebSocket, msg: Dict[str, Any]) -> None:
    """Synthesize one request and answer with audio or an error frame."""
    request = TTSRequest(
        text=str(msg.get("text") or ""),
        voice=msg.get("voice"),
        speed=float(msg.get("speed") or 1.0),
    )
    if not request.text.strip():
        await ws.send_json(
            {"type": "error", "message": "text is required"}
        )
        return
    logger.info("TTS ws request (%s)", summarize_text(request.text))
    client = resolve_tts_client(require_runtime_registry(ws))
    try:
        response = await asyncio.to_thread(
            client.invoke, build_tts_envelope(request)
        )
    except Exception as exc:
        logger.error("Error synthesizing speech: %s", exc)
        await ws.send_json({"type": "error", "message": str(exc)})
        return
    if response.status is not EnvelopeStatus.SUCCEEDED:
        message = (
            response.error.message
            if response.error
            else "TTS request failed"
        )
        await ws.send_json(
            {
                "type": "error",
                "message": message,
                "status": tts_error_status_code(response),
            }
        )
        return
    audio = base64.b64encode(tts_response_audio(response)).decode("ascii")
    await ws.send_json({"type": "audio", "data": audio})


async def _handle(ws: WebSocket, msg: Dict[str, Any]) -> None:
    """Dispatch one client frame."""
    if msg.get("type") != "synthesize":
        await ws.send_json(
            {"type": "error", "message": "unsupported message type"}
        )
        return
    await _synthesize(ws, msg)


@router.websocket("/ws")
async def tts_websocket(ws: WebSocket) -> None:
    """Serve persistent TTS synthesis for the chat client."""
    if websocket_auth_failed(ws):
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await ws.accept()
    while True:
        try:
            msg = await ws.receive_json()
        except WebSocketDisconnect:
            return
        except ValueError:
            continue
        await _handle(ws, msg)


__all__ = ["router", "tts_websocket"]
