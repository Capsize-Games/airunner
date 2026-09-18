"""Speech-to-text routes backed by the runtime registry."""

import base64
from typing import List

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
            raise HTTPException(
                status_code=runtime_error_status(response),
                detail=response.error.message
                if response.error
                else "STT request failed",
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
            status_code=500, detail=f"Error transcribing audio: {str(e)}"
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
        models = []

        for model_id, model_spec in registry.models.items():
            if model_spec.model_type is ModelType.SPEECH_TO_TEXT:
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
    while True:
        try:
            message = await websocket.receive()
        except WebSocketDisconnect:
            break
        if message.get("type") == "websocket.disconnect":
            break
        await answer_stream_frame(websocket, message)
    logger.info("STT WebSocket connection closed")
