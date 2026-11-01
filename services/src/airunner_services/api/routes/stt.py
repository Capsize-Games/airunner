"""Speech-to-text routes backed by the runtime registry."""

import base64
from pathlib import Path
from typing import Any, List

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from airunner_services.data.tenant import (
    get_tenant_key,
    reset_tenant_key,
    set_tenant_key,
)
from airunner_services.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind
from airunner_common.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

from .stt_helpers import (
    answer_stream_frame,
    require_runtime_registry,
    resolve_stt_client,
    response_status_is,
    runtime_error_status,
)
from .stt_models import ModelInfo, TranscriptionResponse
from .ws_auth import websocket_auth_failed

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
router = APIRouter()


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...), req: Request = None
):
    """
    Transcribe audio file.

    Args:
        audio: Audio file upload
        req: FastAPI request for accessing app state

    Returns:
        Transcribed text
    """
    try:
        audio_data = await audio.read()
        logger.info(
            "STT request received (filename_present=%s, size_bytes=%d)",
            bool(audio.filename),
            len(audio_data),
        )
        client = resolve_stt_client(require_runtime_registry(req))
        response = client.invoke(
            RequestEnvelope(
                runtime=RuntimeKind.STT,
                action=RuntimeAction.INVOKE,
                provider="local",
                payload={
                    "audio_b64": base64.b64encode(audio_data).decode(
                        "ascii"
                    ),
                    "mime_type": audio.content_type
                    or "application/octet-stream",
                },
            )
        )
        if not response_status_is(response, EnvelopeStatus.SUCCEEDED):
            if response.error:
                logger.warning(
                    "STT transcribe failed: %s", response.error.message
                )
            raise HTTPException(
                status_code=runtime_error_status(response),
                detail="STT request failed",
            )
        return TranscriptionResponse(
            text=response.payload.get("text", ""),
            language=response.payload.get("language"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise HTTPException(
            status_code=500, detail="STT request failed"
        )


@router.get("/models", response_model=List[ModelInfo])
async def list_models(req: Request):
    """
    List available STT models.

    Args:
        req: FastAPI request for accessing app state

    Returns:
        List of available models
    """
    try:
        # Import here to avoid circular imports
        from airunner_services.model_management.model_registry import (
            ModelRegistry,
            ModelType,
        )

        registry = ModelRegistry()
        loaded_model_ids = _loaded_stt_model_ids(
            getattr(req.app.state, "runtime_registry", None)
        )
        models = []

        for model_id, model_spec in registry.models.items():
            if model_spec.model_type is ModelType.SPEECH_TO_TEXT:
                models.append(
                    ModelInfo(
                        id=model_id,
                        name=model_spec.name,
                        loaded=_model_matches_loaded_identity(
                            model_id, model_spec, loaded_model_ids
                        ),
                    )
                )

        return models
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to list models"
        )


def _loaded_stt_model_ids(runtime_registry: Any) -> set[str]:
    """Return identity aliases only when the registered runtime is ready."""
    if runtime_registry is None:
        return set()
    try:
        client = resolve_stt_client(runtime_registry)
        health = client.healthcheck()
    except Exception as exc:
        logger.debug("STT model status is unavailable: %s", exc)
        return set()
    status_value = getattr(health, "status", None)
    health_status = getattr(status_value, "value", status_value)
    if str(health_status).lower() != "ready":
        return set()
    health_metadata = getattr(health, "metadata", None)
    metadata = health_metadata if isinstance(health_metadata, dict) else {}
    identifiers = set()
    for key in ("model_id", "model_path"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            identifiers.add(value.strip())
            identifiers.add(Path(value.strip()).name)
    return identifiers


def _model_matches_loaded_identity(
    model_id: str, model_spec: Any, loaded_model_ids: set[str]
) -> bool:
    """Match runtime metadata against the catalog's model identifiers."""
    if not loaded_model_ids:
        return False
    aliases = {
        str(value).strip()
        for value in (
            model_id,
            getattr(model_spec, "model_id", None),
            getattr(model_spec, "huggingface_id", None),
            getattr(model_spec, "preferred_download_filename", None),
        )
        if isinstance(value, str) and value.strip()
    }
    return bool(aliases.intersection(loaded_model_ids))


@router.websocket("/stream")
async def websocket_transcription(websocket: WebSocket) -> None:
    """Transcribe streamed audio over one WebSocket.

    A client sends either a JSON frame
    ``{"type": "transcribe", "audio": "<base64>", "language"}`` or a raw
    binary frame of audio bytes, and receives one
    ``{"type": "transcript", "text", "language", "final"}`` frame per
    utterance -- or ``{"type": "error", "message"}`` on failure. This is
    the microphone path behind the chat surface's STT toggle.
    """
    if websocket_auth_failed(websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await websocket.accept()
    logger.info("STT WebSocket connection established")
    conn_token = set_tenant_key(get_tenant_key())
    try:
        while True:
            try:
                message = await websocket.receive()
            except WebSocketDisconnect:
                break
            if message.get("type") == "websocket.disconnect":
                break
            await answer_stream_frame(websocket, message)
    finally:
        reset_tenant_key(conn_token)
    logger.info("STT WebSocket connection closed")
