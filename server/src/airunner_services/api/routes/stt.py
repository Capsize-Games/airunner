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
)

from airunner_services.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

from .stt_helpers import (
    require_runtime_registry,
    resolve_stt_client,
    response_status_is,
    runtime_error_status,
)
from .stt_models import ModelInfo, TranscriptionResponse

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
router = APIRouter()


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(audio: UploadFile = File(...), req: Request = None):
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
                    "audio_b64": base64.b64encode(audio_data).decode("ascii"),
                    "mime_type": audio.content_type
                    or "application/octet-stream",
                },
            )
        )
        if not response_status_is(response, EnvelopeStatus.SUCCEEDED):
            raise HTTPException(
                status_code=runtime_error_status(response),
                detail=(
                    response.error.message
                    if response.error
                    else "STT request failed"
                ),
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
async def websocket_transcription(websocket: WebSocket):
    """
    WebSocket endpoint for real-time transcription.

    Args:
        websocket: WebSocket connection
    """
    await websocket.accept()
    logger.info("STT WebSocket connection established")

    try:
        from airunner_services.api.services.stt_services import (
            STTAPIService,
        )
        from airunner_services.contract_enums import SignalCode
        from airunner_services.utils.application.signal_mediator import (
            SignalMediator,
        )

        stt_service = STTAPIService()
        mediator = SignalMediator()

        async def on_transcription_chunk(data: dict):
            """Send transcription chunks to WebSocket client."""
            text = data.get("text")
            is_final = data.get("is_final", False)
            if text:
                await websocket.send_json(
                    {"type": "chunk", "text": text, "final": is_final}
                )

        mediator.register(SignalCode.STT_CHUNK_SIGNAL, on_transcription_chunk)

        try:
            while True:
                data = await websocket.receive_bytes()
                logger.debug(f"Received audio chunk: {len(data)} bytes")
                stt_service.emit_signal(
                    SignalCode.STT_TRANSCRIBE_CHUNK_SIGNAL,
                    {"audio_chunk": data},
                )
        except WebSocketDisconnect:
            logger.info("STT WebSocket connection closed")
        finally:
            mediator.unregister(
                SignalCode.STT_CHUNK_SIGNAL,
                on_transcription_chunk,
            )
    except Exception as e:
        logger.error(f"STT WebSocket error: {e}")
        try:
            await websocket.send_json(
                {"type": "error", "content": f"Server error: {str(e)}"}
            )
        except Exception:
            pass
