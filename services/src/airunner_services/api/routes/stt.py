"""Speech-to-text routes backed by the runtime registry."""

import base64
from typing import List, Optional

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel

from airunner_services.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind
from airunner_services.runtimes.registry import RuntimeRegistry
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
router = APIRouter()


# ====================
# Pydantic Models
# ====================


class TranscriptionResponse(BaseModel):
    """Transcription response."""

    text: str
    language: Optional[str] = None


class ModelInfo(BaseModel):
    """STT model information."""

    id: str
    name: str
    loaded: bool


# ====================
# Helper Functions
# ====================


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
        raise HTTPException(status_code=503, detail="STT runtime unavailable") from exc


def _runtime_error_status(response) -> int:
    """Map runtime envelope failures to HTTP status codes."""
    error = response.error
    if error and error.code.endswith("_timeout"):
        return 504
    return 500


def _response_status_is(response: object, expected: EnvelopeStatus) -> bool:
    """Return True when one envelope-like response matches a status."""
    status = getattr(response, "status", None)
    value = getattr(status, "value", status)
    return str(value or "").strip().lower() == expected.value


# ====================
# API Endpoints
# ====================


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
                    "mime_type": audio.content_type or "application/octet-stream",
                },
            )
        )
        if not _response_status_is(response, EnvelopeStatus.SUCCEEDED):
            raise HTTPException(
                status_code=_runtime_error_status(response),
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

        # Get available models from ModelRegistry
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
        from airunner_services.api.services.stt_services import STTAPIService
        from airunner_services.contract_enums import SignalCode
        from airunner_services.utils.application.signal_mediator import SignalMediator

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

        # Register signal handler for streaming
        mediator.register(SignalCode.STT_CHUNK_SIGNAL, on_transcription_chunk)

        try:
            while True:
                # Receive audio chunks from client
                data = await websocket.receive_bytes()
                logger.debug(f"Received audio chunk: {len(data)} bytes")

                # Emit STT request for chunk
                stt_service.emit_signal(
                    SignalCode.STT_TRANSCRIBE_CHUNK_SIGNAL,
                    {"audio_chunk": data},
                )

        except WebSocketDisconnect:
            logger.info("STT WebSocket connection closed")

        finally:
            # Cleanup signal handler
            mediator.unregister(
                SignalCode.STT_CHUNK_SIGNAL, on_transcription_chunk
            )

    except Exception as e:
        logger.error(f"STT WebSocket error: {e}")
        try:
            await websocket.send_json(
                {"type": "error", "content": f"Server error: {str(e)}"}
            )
        except:
            pass

            # TODO: Implement streaming STT
            # For now, just acknowledge
            await websocket.send_json(
                {
                    "type": "transcription",
                    "text": "Streaming transcription pending implementation",
                }
            )

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
