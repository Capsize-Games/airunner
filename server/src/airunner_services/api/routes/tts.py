"""Text-to-Speech endpoints backed by the daemon runtime registry."""

from __future__ import annotations

import asyncio
import base64
import io
from typing import List

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse

from airunner_services.ipc.messages import EnvelopeStatus
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.utils.application.log_hygiene import summarize_text

from .tts_helpers import (
    build_tts_envelope,
    require_runtime_registry,
    resolve_tts_client,
    tts_error_status_code,
    tts_response_audio,
)
from .tts_daemon_ws import router as tts_daemon_ws_router
from .tts_models import ModelInfo, TTSRequest

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
router = APIRouter()
router.include_router(tts_daemon_ws_router)


@router.post("/synthesize")
async def synthesize_speech(request: TTSRequest, req: Request):
    """
    Convert text to speech.

    Args:
        request: TTS request
        req: FastAPI request for accessing app state

    Returns:
        Audio file (WAV)
    """
    logger.info(
        "TTS request received (%s)",
        summarize_text(request.text),
    )
    client = resolve_tts_client(require_runtime_registry(req))
    try:
        envelope = build_tts_envelope(request)
        response = await asyncio.to_thread(client.invoke, envelope)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error synthesizing speech: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error synthesizing speech: {str(e)}",
        )
    if response.status is not EnvelopeStatus.SUCCEEDED:
        detail = (
            response.error.message if response.error else "TTS request failed"
        )
        raise HTTPException(
            status_code=tts_error_status_code(response),
            detail=detail,
        )
    audio_data = tts_response_audio(response)
    audio_io = io.BytesIO(audio_data)
    return StreamingResponse(audio_io, media_type="audio/wav")


@router.get("/models", response_model=List[ModelInfo])
async def list_models(req: Request):
    """
    List available TTS models.

    Args:
        req: FastAPI request for accessing app state

    Returns:
        List of available models
    """
    try:
        from airunner_services.model_management.model_registry import (
            ModelRegistry,
        )

        registry = ModelRegistry()
        models = [
            ModelInfo(
                id=model_id,
                name=model_spec.name,
                loaded=False,
            )
            for model_id, model_spec in registry.models.items()
            if model_spec.model_type.value == "tts"
        ]
        return models
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error listing models: {str(e)}"
        )


# ── WebSocket endpoint ────────────────────────────────────────────────────


@router.websocket("/ws")
async def tts_websocket(websocket: WebSocket):
    """WebSocket endpoint for TTS synthesis.

    Protocol
    --------
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
                text = str(data.get("text", "")).strip()
                if not text:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "No text provided",
                        }
                    )
                    continue

                logger.info(
                    "TTS WS request (%s)",
                    summarize_text(text),
                )
                try:
                    client = resolve_tts_client(
                        require_runtime_registry(websocket),
                    )
                    request = TTSRequest(
                        text=text,
                        voice=data.get("voice"),
                        speed=float(data.get("speed", 1.0)),
                    )
                    envelope = build_tts_envelope(request)
                    response = await asyncio.to_thread(
                        client.invoke,
                        envelope,
                    )
                except HTTPException as exc:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": exc.detail,
                        }
                    )
                    continue
                except Exception as exc:
                    logger.error(f"TTS WS error: {exc}")
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Synthesis failed: {str(exc)}",
                        }
                    )
                    continue

                if response.status is not EnvelopeStatus.SUCCEEDED:
                    detail = (
                        response.error.message
                        if response.error
                        else "TTS request failed"
                    )
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": detail,
                        }
                    )
                    continue

                try:
                    audio_data = tts_response_audio(response)
                    audio_b64 = base64.b64encode(audio_data).decode("ascii")
                    await websocket.send_json(
                        {
                            "type": "audio",
                            "data": audio_b64,
                            "format": "wav",
                        }
                    )
                except HTTPException as exc:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": exc.detail,
                        }
                    )
            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    }
                )
    except WebSocketDisconnect:
        logger.info("TTS WebSocket disconnected")
    except Exception as exc:
        logger.error(f"TTS WebSocket error: {exc}")
