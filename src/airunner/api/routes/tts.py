"""
Text-to-Speech endpoints.

Integrates with TTSAPIService for speech synthesis.
"""

import logging
import asyncio
import io
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# ====================
# Pydantic Models
# ====================


class TTSRequest(BaseModel):
    """TTS request."""

    text: str
    voice: Optional[str] = None
    speed: float = 1.0


class ModelInfo(BaseModel):
    """TTS model information."""

    id: str
    name: str
    loaded: bool


# ====================
# Helper Functions
# ====================


def get_tts_service(request: Request):
    """Get TTSAPIService from FastAPI app state."""
    if hasattr(request.app.state, "airunner_app"):
        from airunner.components.tts.api.tts_services import TTSAPIService

        return TTSAPIService()
    return None


# ====================
# API Endpoints
# ====================


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
    logger.info(f"TTS request: {request.text[:50]}...")

    tts_service = get_tts_service(req)
    if not tts_service:
        raise HTTPException(
            status_code=503, detail="TTS service not available"
        )

    try:
        from airunner.enums import SignalCode
        from airunner.utils.application.signal_mediator import SignalMediator

        # Create future for audio data
        audio_future = asyncio.Future()

        def on_tts_complete(data: dict):
            """Callback for TTS completion."""
            audio_data = data.get("audio")
            if audio_data and not audio_future.done():
                audio_future.set_result(audio_data)

        # Register signal handler
        mediator = SignalMediator()
        mediator.register(SignalCode.TTS_COMPLETE_SIGNAL, on_tts_complete)

        try:
            # Emit TTS request
            tts_service.emit_signal(
                SignalCode.TTS_GENERATE_SIGNAL,
                {
                    "text": request.text,
                    "voice": request.voice,
                    "speed": request.speed,
                },
            )

            # Wait for audio (with timeout)
            try:
                audio_data = await asyncio.wait_for(audio_future, timeout=60.0)
            except asyncio.TimeoutError:
                raise HTTPException(
                    status_code=504, detail="TTS request timed out"
                )

            # Return audio as WAV
            audio_io = io.BytesIO(audio_data)
            return StreamingResponse(audio_io, media_type="audio/wav")

        finally:
            mediator.unregister(
                SignalCode.TTS_COMPLETE_SIGNAL, on_tts_complete
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error synthesizing speech: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error synthesizing speech: {str(e)}"
        )


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
        from airunner.components.model_management.model_registry import (
            ModelRegistry,
        )
        from airunner.components.tts.data.tts_generator_settings import (
            TTSGeneratorSettings,
        )

        # Get current model from settings
        settings = TTSGeneratorSettings.objects.first()
        current_model = settings.model_version if settings else None

        # Get available models from ModelRegistry
        registry = ModelRegistry()
        models = []

        for model_id, model_spec in registry.models.items():
            if model_spec.model_type.value == "tts":
                models.append(
                    ModelInfo(
                        id=model_id,
                        name=model_spec.name,
                        loaded=(model_id == current_model),
                    )
                )

        return models

    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error listing models: {str(e)}"
        )
