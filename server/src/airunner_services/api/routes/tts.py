"""Text-to-Speech endpoints backed by the daemon runtime registry."""

from __future__ import annotations

import asyncio
import io
from typing import List

from fastapi import APIRouter, HTTPException, Request
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
from .tts_models import ModelInfo, TTSRequest

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
router = APIRouter()


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
            response.error.message
            if response.error
            else "TTS request failed"
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
