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

from airunner_services.data.tenant import (
    get_tenant_key,
    reset_tenant_key,
    set_tenant_key,
)
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

_MIN_TTS_SPEED = 0.25
_MAX_TTS_SPEED = 4.0
_SYNTHESIS_TIMEOUT_SECONDS = 120.0


async def _synthesize(
    ws: WebSocket,
    msg: Dict[str, Any],
    lock: asyncio.Lock | None = None,
    timeout: float = _SYNTHESIS_TIMEOUT_SECONDS,
) -> None:
    """Synthesize one request and answer with audio or an error frame.

    The speed is validated before the runtime is touched so a bad
    value answers with an error frame instead of dropping the
    connection, and one connection synthesizes at most one utterance
    at a time behind ``lock`` with a bounded wait (issue #2427).
    """
    raw_speed = msg.get("speed", 1.0)
    try:
        speed = float(raw_speed if raw_speed is not None else 1.0)
    except (TypeError, ValueError):
        await ws.send_json(
            {"type": "error", "message": "invalid_speed"}
        )
        return
    if not (_MIN_TTS_SPEED <= speed <= _MAX_TTS_SPEED):
        await ws.send_json(
            {"type": "error", "message": "invalid_speed"}
        )
        return
    request = TTSRequest(
        text=str(msg.get("text") or ""),
        voice=msg.get("voice"),
        speed=speed,
    )
    if not request.text.strip():
        await ws.send_json(
            {"type": "error", "message": "text is required"}
        )
        return
    logger.info("TTS ws request (%s)", summarize_text(request.text))
    client = resolve_tts_client(require_runtime_registry(ws))
    active = lock if lock is not None else asyncio.Lock()
    try:
        async with active:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.invoke, build_tts_envelope(request)
                ),
                timeout=timeout,
            )
    except asyncio.TimeoutError:
        logger.warning("TTS synthesis timed out")
        await ws.send_json(
            {"type": "error", "message": "synthesis_timeout"}
        )
        return
    except Exception as exc:
        logger.error("Error synthesizing speech: %s", exc)
        await ws.send_json({"type": "error", "message": "synthesis_failed"})
        return
    if response.status is not EnvelopeStatus.SUCCEEDED:
        if response.error:
            logger.warning("TTS request failed: %s", response.error.message)
        await ws.send_json(
            {
                "type": "error",
                "message": "synthesis_failed",
                "status": tts_error_status_code(response),
            }
        )
        return
    audio = base64.b64encode(tts_response_audio(response)).decode("ascii")
    await ws.send_json({"type": "audio", "data": audio})


async def _handle(
    ws: WebSocket,
    msg: Dict[str, Any],
    lock: asyncio.Lock | None = None,
    timeout: float = _SYNTHESIS_TIMEOUT_SECONDS,
) -> None:
    """Dispatch one client frame."""
    if msg.get("type") != "synthesize":
        await ws.send_json(
            {"type": "error", "message": "unsupported message type"}
        )
        return
    await _synthesize(ws, msg, lock, timeout)


@router.websocket("/ws")
async def tts_websocket(ws: WebSocket) -> None:
    """Serve persistent TTS synthesis for the chat client."""
    if websocket_auth_failed(ws):
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await ws.accept()
    synth_lock = asyncio.Lock()
    conn_token = set_tenant_key(get_tenant_key())
    try:
        while True:
            try:
                msg = await ws.receive_json()
            except WebSocketDisconnect:
                return
            except ValueError:
                continue
            await _handle(ws, msg, synth_lock)
    finally:
        reset_tenant_key(conn_token)


__all__ = ["router", "tts_websocket"]
