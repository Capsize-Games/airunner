"""Text-to-Speech endpoints backed by the daemon runtime registry."""

from __future__ import annotations

import asyncio
import io
from pathlib import Path
from typing import Any, List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

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
from airunner_services.runtimes.contracts import (
    RuntimeHealthStatus,
    RuntimeKind,
    RuntimeMode,
)

from .tts_models import (
    ModelInfo,
    TTSHTTPRequest,
    VoiceCatalogResponse,
)

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
router = APIRouter()


@router.post("/synthesize")
async def synthesize_speech(request: TTSHTTPRequest, req: Request):
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
            detail="TTS request failed",
        )
    if response.status is not EnvelopeStatus.SUCCEEDED:
        if response.error:
            logger.warning("TTS request failed: %s", response.error.message)
        raise HTTPException(
            status_code=tts_error_status_code(response),
            detail="TTS request failed",
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
            ModelType,
        )

        registry = ModelRegistry()
        loaded_model_ids = _loaded_tts_model_ids(
            getattr(req.app.state, "runtime_registry", None)
        )
        models = [
            ModelInfo(
                id=model_id,
                name=model_spec.name,
                loaded=_model_matches_loaded_identity(
                    model_id, model_spec, loaded_model_ids
                ),
            )
            for model_id, model_spec in registry.models.items()
            if model_spec.model_type is ModelType.TEXT_TO_SPEECH
        ]
        return models
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to list models"
        )


def _loaded_tts_model_ids(runtime_registry: Any) -> set[str]:
    """Return model aliases only when the TTS runtime reports READY."""
    if runtime_registry is None:
        return set()
    try:
        client = resolve_tts_client(runtime_registry)
        health = client.healthcheck()
    except Exception as exc:
        logger.debug("TTS model status is unavailable: %s", exc)
        return set()
    status = getattr(health, "status", None)
    status = getattr(status, "value", status)
    if str(status).lower() != RuntimeHealthStatus.READY.value:
        return set()
    metadata = getattr(health, "metadata", None)
    metadata = metadata if isinstance(metadata, dict) else {}
    identities: set[str] = set()
    for key in ("model_id", "model_path", "model_type"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            identities.add(value.strip())
            if key == "model_path":
                identities.add(Path(value.strip()).name)
    return identities


def _model_matches_loaded_identity(
    model_id: str, model_spec: Any, loaded_model_ids: set[str]
) -> bool:
    """Match runtime health metadata against a model catalog entry."""
    if not loaded_model_ids:
        return False
    aliases = {
        str(value).strip()
        for value in (
            model_id,
            getattr(model_spec, "name", None),
            getattr(model_spec, "model_id", None),
            getattr(model_spec, "huggingface_id", None),
            getattr(model_spec, "preferred_download_filename", None),
        )
        if isinstance(value, str) and value.strip()
    }
    return bool(aliases.intersection(loaded_model_ids))


@router.get("/voices", response_model=VoiceCatalogResponse)
async def list_voices(req: Request) -> VoiceCatalogResponse:
    """Return voice IDs reported by an already-ready local TTS runtime."""
    registry = require_runtime_registry(req)
    for mode in (RuntimeMode.LOCAL_FALLBACK, RuntimeMode.SIDECAR):
        try:
            client = registry.resolve(
                RuntimeKind.TTS,
                provider="local",
                deployment_mode=mode.value,
            )
            health = client.healthcheck()
        except Exception as exc:
            logger.debug("TTS voice metadata is unavailable: %s", exc)
            continue
        if health.status is not RuntimeHealthStatus.READY:
            continue
        voice_ids = health.metadata.get("voice_ids")
        if not isinstance(voice_ids, (list, tuple)):
            continue
        try:
            return VoiceCatalogResponse(voices=voice_ids)
        except ValidationError as exc:
            logger.warning("TTS voice metadata is invalid: %s", exc)
            continue
    raise HTTPException(
        status_code=503, detail="tts_voice_catalog_unavailable"
    )
