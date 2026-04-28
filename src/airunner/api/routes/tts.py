"""
Text-to-Speech endpoints.

Routes synthesis through the daemon runtime registry.
"""

import asyncio
import base64
import io
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from airunner.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner.runtimes.base import RuntimeClient
from airunner.runtimes.contracts import (
    RuntimeAction,
    RuntimeKind,
    TTSInvocationRequest,
)
from airunner.runtimes.registry import RuntimeRegistry
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
router = APIRouter()


# ====================
# Pydantic Models
# ====================


class TTSRequest(BaseModel):
    """TTS request."""

    text: str
    voice: Optional[str] = None
    speed: float = 1.0
    model: Optional[str] = None
    model_type: Optional[str] = None
    request_id: Optional[str] = None


class ModelInfo(BaseModel):
    """TTS model information."""

    id: str
    name: str
    loaded: bool


# ====================
# Helper Functions
# ====================


def get_runtime_registry(request: Request) -> Optional[RuntimeRegistry]:
    """Return the runtime registry attached to the FastAPI app."""
    return getattr(request.app.state, "runtime_registry", None)


def require_runtime_registry(request: Request) -> RuntimeRegistry:
    """Return the runtime registry or raise when it is unavailable."""
    runtime_registry = get_runtime_registry(request)
    if runtime_registry is None:
        raise HTTPException(status_code=503, detail="TTS runtime unavailable")
    return runtime_registry


def resolve_tts_client(registry: RuntimeRegistry) -> RuntimeClient:
    """Resolve the explicit sidecar TTS runtime client."""
    try:
        return registry.resolve(
            RuntimeKind.TTS,
            provider="local",
            deployment_mode="sidecar",
        )
    except KeyError as exc:
        raise HTTPException(status_code=503, detail="TTS runtime unavailable") from exc


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

    client = resolve_tts_client(require_runtime_registry(req))
    try:
        invocation = TTSInvocationRequest(
            text=request.text,
            model=request.model,
            voice=request.voice,
            speed=request.speed,
            metadata={
                "model_type": request.model_type,
            }
            if request.model_type
            else {},
        )
        response = await asyncio.to_thread(
            client.invoke,
            RequestEnvelope(
                request_id=request.request_id or str(uuid4()),
                runtime=RuntimeKind.TTS,
                action=RuntimeAction.INVOKE,
                provider="local",
                payload=invocation.model_dump(),
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error synthesizing speech: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error synthesizing speech: {str(e)}"
        )

    if response.status is EnvelopeStatus.FAILED:
        detail = response.error.message if response.error else "TTS request failed"
        status_code = 504 if response.error and response.error.code.endswith("_timeout") else 502
        raise HTTPException(status_code=status_code, detail=detail)
    if response.status is EnvelopeStatus.CANCELLED:
        raise HTTPException(status_code=409, detail="TTS request cancelled")

    audio_b64 = str((response.payload or {}).get("audio_b64") or "")
    if not audio_b64:
        raise HTTPException(status_code=502, detail="TTS runtime returned no audio")

    audio_data = base64.b64decode(audio_b64)
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
        # Import here to avoid circular imports
        from airunner.components.model_management.model_registry import (
            ModelRegistry,
        )

        # Get available models from ModelRegistry
        registry = ModelRegistry()
        models = []

        for model_id, model_spec in registry.models.items():
            if model_spec.model_type.value == "tts":
                models.append(
                    ModelInfo(
                        id=model_id,
                        name=model_spec.name,
                        loaded=False,  # TODO: Get actual loaded state
                    )
                )

        return models

    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error listing models: {str(e)}"
        )
