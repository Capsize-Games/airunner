"""Text-to-Speech endpoints backed by the daemon runtime registry."""

from __future__ import annotations

import asyncio
from typing import List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
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
from airunner_services.runtimes.espeak_cli_renderer import EspeakRenderError
from airunner_services.runtimes.contracts import (
    RuntimeHealthStatus,
    RuntimeKind,
    RuntimeMode,
)
from airunner_services.runtimes.tts_capabilities import (
    TTS_BACKEND_UNAVAILABLE_CODE,
    is_deferred_tts_model_type,
    normalize_tts_model_type,
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
    if is_deferred_tts_model_type(request.model_type):
        raise HTTPException(
            status_code=503,
            detail="tts_backend_unavailable",
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
        detail = "TTS request failed"
        if (
            response.error
            and response.error.code == TTS_BACKEND_UNAVAILABLE_CODE
        ):
            detail = TTS_BACKEND_UNAVAILABLE_CODE
        raise HTTPException(
            status_code=tts_error_status_code(response),
            detail=detail,
        )
    audio_data = tts_response_audio(response)
    return Response(content=audio_data, media_type="audio/wav")


@router.get("/models", response_model=List[ModelInfo])
async def list_models(req: Request):
    """List models with a supported HTTP audio synthesis path."""
    runtime_registry = getattr(req.app.state, "runtime_registry", None)
    if runtime_registry is None:
        return []
    for mode in (RuntimeMode.LOCAL_FALLBACK, RuntimeMode.SIDECAR):
        try:
            client = runtime_registry.resolve(
                RuntimeKind.TTS,
                provider="local",
                deployment_mode=mode.value,
            )
            health = client.healthcheck()
        except Exception as exc:
            logger.debug("TTS model metadata is unavailable: %s", exc)
            continue
        if health.status is not RuntimeHealthStatus.READY:
            continue
        metadata = health.metadata
        if metadata.get("capability_status") == "deferred":
            continue
        if is_deferred_tts_model_type(metadata.get("model_type")):
            continue
        model_id = metadata.get("model_id")
        if not isinstance(model_id, str) or not model_id.strip():
            continue
        model_name = metadata.get("model_name")
        if not isinstance(model_name, str) or not model_name.strip():
            model_name = model_id.strip()
        return [
            ModelInfo(
                id=model_id.strip(),
                name=model_name.strip(),
                loaded=True,
            )
        ]
    # The built-in eSpeak manager is playback-only; OpenVoice is deferred.
    # Neither can be represented here as an HTTP audio synthesis backend.
    return []


@router.get("/voices", response_model=VoiceCatalogResponse)
async def list_voices(
    req: Request, model_type: str | None = None
) -> VoiceCatalogResponse:
    """Return explicit eSpeak IDs or metadata from an already-ready runtime."""
    if model_type is not None:
        normalized_model = normalize_tts_model_type(model_type)
        if is_deferred_tts_model_type(normalized_model):
            raise HTTPException(
                status_code=503,
                detail=TTS_BACKEND_UNAVAILABLE_CODE,
            )
        if normalized_model not in {"espeak", "espeak-ng", "espeak_ng"}:
            raise HTTPException(
                status_code=422,
                detail="tts_model_type_unsupported",
            )
        registry = require_runtime_registry(req)
        try:
            client = registry.resolve(
                RuntimeKind.TTS,
                provider="local",
                deployment_mode=RuntimeMode.LOCAL_FALLBACK.value,
            )
        except Exception as exc:
            logger.debug("eSpeak voice catalog is unavailable: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="tts_voice_catalog_unavailable",
            ) from exc
        list_voice_ids = getattr(client, "list_voice_ids", None)
        if not callable(list_voice_ids):
            raise HTTPException(
                status_code=503,
                detail="tts_voice_catalog_unavailable",
            )
        try:
            return VoiceCatalogResponse(
                voices=await asyncio.to_thread(
                    list_voice_ids, model_type
                )
            )
        except EspeakRenderError as exc:
            status_code = 504 if exc.code == "tts_timeout" else 503
            raise HTTPException(
                status_code=status_code,
                detail="tts_voice_catalog_unavailable",
            ) from exc

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
        metadata = health.metadata
        if metadata.get("capability_status") == "deferred":
            continue
        if is_deferred_tts_model_type(metadata.get("model_type")):
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
