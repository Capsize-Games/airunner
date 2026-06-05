"""Helper utilities for text-to-speech endpoints."""

from __future__ import annotations

import base64
from uuid import uuid4

from fastapi import HTTPException

from airunner_services.ipc.messages import (
    EnvelopeStatus,
    RequestEnvelope,
    ResponseEnvelope,
)
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import (
    RuntimeAction,
    RuntimeKind,
    RuntimeMode,
    TTSInvocationRequest,
)
from airunner_services.runtimes.registry import RuntimeRegistry

from .tts_models import TTSRequest


def build_tts_invocation(request: TTSRequest) -> TTSInvocationRequest:
    """Construct a TTS invocation request from the API payload."""
    return TTSInvocationRequest(
        text=request.text,
        model=request.model,
        voice=request.voice,
        speed=request.speed,
        metadata=(
            {"model_type": request.model_type} if request.model_type else {}
        ),
    )


def tts_error_status_code(response: ResponseEnvelope) -> int:
    """Map TTS response status to the appropriate HTTP status code."""
    if response.status is EnvelopeStatus.CANCELLED:
        return 409
    if response.status is EnvelopeStatus.FAILED:
        if response.error and response.error.code.endswith("_timeout"):
            return 504
        return 502
    return 502


def tts_response_audio(response: ResponseEnvelope) -> bytes:
    """Decode and return audio bytes from a TTS runtime response."""
    audio_b64 = str((response.payload or {}).get("audio_b64") or "")
    if not audio_b64:
        raise HTTPException(
            status_code=502,
            detail="TTS runtime returned no audio",
        )
    return base64.b64decode(audio_b64)


def get_runtime_registry(request) -> RuntimeRegistry | None:
    """Return the runtime registry attached to the FastAPI app."""
    return getattr(request.app.state, "runtime_registry", None)


def require_runtime_registry(request) -> RuntimeRegistry:
    """Return the runtime registry or raise when it is unavailable."""
    runtime_registry = get_runtime_registry(request)
    if runtime_registry is None:
        raise HTTPException(status_code=503, detail="TTS runtime unavailable")
    return runtime_registry


def resolve_tts_client(registry: RuntimeRegistry) -> RuntimeClient:
    """Resolve the preferred TTS runtime client for this process."""
    for deployment_mode in (
        RuntimeMode.LOCAL_FALLBACK.value,
        RuntimeMode.SIDECAR.value,
    ):
        try:
            return registry.resolve(
                RuntimeKind.TTS,
                provider="local",
                deployment_mode=deployment_mode,
            )
        except KeyError:
            continue
    raise HTTPException(status_code=503, detail="TTS runtime unavailable")


def build_tts_envelope(request: TTSRequest) -> RequestEnvelope:
    """Build the runtime envelope for a TTS invocation."""
    invocation = build_tts_invocation(request)
    return RequestEnvelope(
        request_id=request.request_id or str(uuid4()),
        runtime=RuntimeKind.TTS,
        action=RuntimeAction.INVOKE,
        provider="local",
        payload=invocation.model_dump(),
    )
