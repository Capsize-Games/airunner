"""Helper utilities for speech-to-text endpoints."""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException, Request, WebSocket

from airunner_services.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import (
    RuntimeAction,
    RuntimeKind,
)
from airunner_services.runtimes.registry import RuntimeRegistry
from airunner_common.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def get_runtime_registry(request: Request) -> Optional[RuntimeRegistry]:
    """Return the runtime registry stored on app state when available."""
    return getattr(request.app.state, "runtime_registry", None)


def require_runtime_registry(request: Request) -> RuntimeRegistry:
    """Return the runtime registry or raise when STT is unavailable."""
    runtime_registry = get_runtime_registry(request)
    if runtime_registry is None:
        raise HTTPException(status_code=503, detail="STT runtime unavailable")
    return runtime_registry


def resolve_stt_client(registry: RuntimeRegistry) -> RuntimeClient:
    """Resolve the configured local STT runtime client."""
    try:
        return registry.resolve(RuntimeKind.STT, provider="local")
    except KeyError as exc:
        raise HTTPException(
            status_code=503, detail="STT runtime unavailable"
        ) from exc


def runtime_error_status(response) -> int:
    """Map runtime envelope failures to HTTP status codes."""
    error = response.error
    if error and error.code.endswith("_timeout"):
        return 504
    return 500


def response_status_is(response: object, expected: EnvelopeStatus) -> bool:
    """Return True when one envelope-like response matches a status."""
    status = getattr(response, "status", None)
    value = getattr(status, "value", status)
    return str(value or "").strip().lower() == expected.value


def build_stt_envelope(
    audio: bytes,
    language: Optional[str],
) -> RequestEnvelope:
    """Build one STT runtime envelope for a single audio buffer."""
    return RequestEnvelope(
        runtime=RuntimeKind.STT,
        action=RuntimeAction.INVOKE,
        provider="local",
        payload={
            "audio_b64": base64.b64encode(audio).decode("ascii"),
            "mime_type": "audio/wav",
            "language": language,
        },
    )


def decode_stream_frame(
    message: Dict[str, Any],
) -> Tuple[Optional[bytes], Optional[str]]:
    """Return ``(audio, language)`` for a frame, or ``(None, None)``.

    Accepts a raw binary frame of audio bytes, or a JSON frame shaped
    ``{"type": "transcribe", "audio": "<base64>", "language"}``.
    """
    raw = message.get("bytes")
    if raw:
        return bytes(raw), None
    text = message.get("text")
    if not text:
        return None, None
    try:
        frame = json.loads(text)
    except ValueError:
        return None, None
    if not isinstance(frame, dict) or frame.get("type") != "transcribe":
        return None, None
    encoded = str(frame.get("audio") or "")
    if not encoded:
        return None, None
    try:
        audio = base64.b64decode(encoded, validate=True)
    except Exception:
        return None, None
    language = frame.get("language")
    return audio, str(language) if language else None


async def _invoke_transcription(
    websocket: WebSocket,
    audio: bytes,
    language: Optional[str],
) -> Optional[str]:
    """Run one buffer through the STT runtime; report failures on the wire."""
    try:
        client = resolve_stt_client(require_runtime_registry(websocket))
        response = await asyncio.to_thread(
            client.invoke, build_stt_envelope(audio, language)
        )
    except HTTPException as exc:
        await websocket.send_json({"type": "error", "message": exc.detail})
        return None
    except Exception as exc:
        logger.error("STT WebSocket error: %s", exc)
        await websocket.send_json({"type": "error", "message": str(exc)})
        return None
    if not response_status_is(response, EnvelopeStatus.SUCCEEDED):
        detail = response.error.message if response.error else "STT failed"
        await websocket.send_json({"type": "error", "message": detail})
        return None
    return str(response.payload.get("text", ""))


async def answer_stream_frame(
    websocket: WebSocket,
    message: Dict[str, Any],
) -> None:
    """Transcribe one received frame and answer with a transcript frame."""
    audio, language = decode_stream_frame(message)
    if audio is None:
        await websocket.send_json(
            {"type": "error", "message": "invalid audio frame"}
        )
        return
    text = await _invoke_transcription(websocket, audio, language)
    if text is None:
        return
    await websocket.send_json(
        {
            "type": "transcript",
            "text": text,
            "language": language,
            "final": True,
        }
    )
