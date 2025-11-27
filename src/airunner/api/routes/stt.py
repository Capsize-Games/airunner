"""
Speech-to-Text endpoints.

Integrates with STTAPIService for audio transcription.
"""
import asyncio
from typing import Optional, List
from fastapi import (
    APIRouter,
    File,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    Request,
)
from pydantic import BaseModel

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.enums import SignalCode
from airunner.utils.application.signal_mediator import SignalMediator

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


def get_stt_service(request: Request):
    """Get STTAPIService from FastAPI app state."""
    if hasattr(request.app.state, "airunner_app"):
        from airunner.components.stt.api.stt_services import STTAPIService
        return STTAPIService()
    return None


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
    logger.info(f"STT request: {audio.filename}")

    stt_service = get_stt_service(req)
    if not stt_service:
        raise HTTPException(
            status_code=503, detail="STT service not available"
        )

    try:
        # Read audio file
        audio_data = await audio.read()

        # Create future for transcription
        transcription_future = asyncio.Future()

        def on_transcription_complete(data: dict):
            """Callback for transcription completion."""
            text = data.get("text")
            language = data.get("language")
            if text and not transcription_future.done():
                transcription_future.set_result(
                    {"text": text, "language": language}
                )

        # Register signal handler
        mediator = SignalMediator()
        mediator.register(
            SignalCode.STT_COMPLETE_SIGNAL, on_transcription_complete
        )

        try:
            # Emit STT request
            stt_service.emit_signal(
                SignalCode.STT_TRANSCRIBE_SIGNAL,
                {"audio_data": audio_data, "filename": audio.filename},
            )

            # Wait for transcription (with timeout)
            try:
                result = await asyncio.wait_for(
                    transcription_future, timeout=120.0
                )
            except asyncio.TimeoutError:
                raise HTTPException(
                    status_code=504, detail="STT request timed out"
                )

            return TranscriptionResponse(
                text=result["text"], language=result.get("language")
            )

        finally:
            mediator.unregister(
                SignalCode.STT_COMPLETE_SIGNAL, on_transcription_complete
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
        from airunner.components.model_management.model_registry import (
            ModelRegistry,
        )

        # Get available models from ModelRegistry
        registry = ModelRegistry()
        models = []

        for model_id, model_spec in registry.models.items():
            if model_spec.model_type.value == "stt":
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
