"""Text-to-Speech WebSocket endpoint backed by the daemon runtime registry."""

from __future__ import annotations

import asyncio
import base64

from fastapi import (
    APIRouter,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)

from airunner_services.ipc.messages import (
    EnvelopeStatus,
    ResponseEnvelope,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.utils.application.log_hygiene import summarize_text

from .tts_helpers import (
    build_tts_envelope,
    require_runtime_registry,
    resolve_tts_client,
    tts_response_audio,
)
from .tts_daemon_ws import router as tts_daemon_ws_router
from .tts_models import TTSRequest

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
router = APIRouter()
router.include_router(tts_daemon_ws_router)


# ── Helpers ────────────────────────────────────────────────────────────────


async def _send_error(websocket: WebSocket, message: str) -> None:
    """Send one error JSON frame."""
    await websocket.send_json({"type": "error", "message": message})


async def _synthesize_speech(
    websocket: WebSocket,
    data: dict,
) -> ResponseEnvelope:
    """Build a TTS request, invoke the runtime client, return response."""
    text = str(data.get("text", "")).strip()
    if not text:
        raise ValueError("No text provided")

    logger.info("TTS WS request (%s)", summarize_text(text))
    client = resolve_tts_client(require_runtime_registry(websocket))
    request = TTSRequest(
        text=text,
        voice=data.get("voice"),
        speed=float(data.get("speed", 1.0)),
    )
    envelope = build_tts_envelope(request)
    return await asyncio.to_thread(client.invoke, envelope)


async def _send_audio_response(
    websocket: WebSocket,
    response: ResponseEnvelope,
) -> None:
    """Send audio data from a successful TTS response."""
    audio_data = tts_response_audio(response)
    audio_b64 = base64.b64encode(audio_data).decode("ascii")
    await websocket.send_json(
        {"type": "audio", "data": audio_b64, "format": "wav"},
    )


async def _send_synthesis_result(
    websocket: WebSocket,
    response: ResponseEnvelope,
) -> None:
    """Send the appropriate response for a synthesis result."""
    if response.status is not EnvelopeStatus.SUCCEEDED:
        detail = (
            response.error.message if response.error else "TTS request failed"
        )
        await _send_error(websocket, detail)
        return

    try:
        await _send_audio_response(websocket, response)
    except HTTPException as exc:
        await _send_error(websocket, exc.detail)


async def _handle_synthesize(
    websocket: WebSocket,
    data: dict,
) -> None:
    """Process one synthesize message — invoke and respond."""
    try:
        response = await _synthesize_speech(websocket, data)
    except ValueError:
        await _send_error(websocket, "No text provided")
        return
    except HTTPException as exc:
        await _send_error(websocket, exc.detail)
        return
    except Exception as exc:
        logger.error("TTS WS error: %s", exc)
        await _send_error(websocket, f"Synthesis failed: {exc}")
        return
    await _send_synthesis_result(websocket, response)


# ── WebSocket endpoint ────────────────────────────────────────────────────


@router.websocket("/ws")
async def tts_websocket(websocket: WebSocket):
    """WebSocket endpoint for TTS synthesis.

    Client → Server::
        {"type": "synthesize", "text": "...", "voice": "...", "speed": 1.0}

    Server → Client (success)::
        {"type": "audio", "data": "<base64-wav>", "format": "wav"}

    Server → Client (error)::
        {"type": "error", "message": "..."}
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            if msg_type == "synthesize":
                await _handle_synthesize(websocket, data)
            else:
                await _send_error(
                    websocket,
                    f"Unknown message type: {msg_type}",
                )
    except WebSocketDisconnect:
        logger.info("TTS WebSocket disconnected")
    except Exception as exc:
        logger.error("TTS WebSocket error: %s", exc)
