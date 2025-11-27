"""
LLM API routes for chat, completion, and model management.

Integrates with LLMAPIService via signal-based architecture.
"""

import asyncio
from typing import List, Optional
from fastapi import (
    APIRouter,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Request,
)
from pydantic import BaseModel

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.components.llm.api.llm_services import LLMAPIService
from airunner.enums import SignalCode, LLMActionType
from airunner.utils.application.signal_mediator import SignalMediator
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.components.llm.data.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner.components.model_management.model_registry import (
    ModelRegistry,
)
from airunner.enums import SignalCode
from airunner.utils.application.signal_mediator import SignalMediator
from airunner.enums import SignalCode
from airunner.enums import SignalCode, LLMActionType
from airunner.utils.application.signal_mediator import SignalMediator
from airunner.components.llm.api.llm_services import LLMAPIService
from airunner.components.llm.managers.llm_request import LLMRequest

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

router = APIRouter()


# ====================
# Pydantic Models
# ====================


class ChatMessage(BaseModel):
    """Chat message."""

    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    """Chat completion request."""

    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False


class ChatCompletionResponse(BaseModel):
    """Chat completion response."""

    content: str
    model: str
    finish_reason: str


class CompletionRequest(BaseModel):
    """Text completion request."""

    prompt: str
    max_tokens: int = 100
    temperature: float = 0.7


class CompletionResponse(BaseModel):
    """Text completion response."""

    text: str
    finish_reason: str


class ModelInfo(BaseModel):
    """LLM model information."""

    id: str
    name: str
    loaded: bool
    size_mb: Optional[int] = None


class ModelLoadRequest(BaseModel):
    """Model load request."""

    model_id: str


# ====================
# Helper Functions
# ====================


def get_llm_service(request: Request):
    """Get LLMAPIService from FastAPI app state."""
    if hasattr(request.app.state, "airunner_app"):
        # Import here to avoid circular imports
        from airunner.components.llm.api.llm_services import LLMAPIService

        return LLMAPIService()
    return None


async def wait_for_llm_response(
    llm_service, prompt: str, llm_request, timeout: float = 120.0
) -> str:
    """
    Send LLM request and wait for response using signal handlers.

    Args:
        llm_service: LLMAPIService instance
        prompt: Prompt text
        llm_request: LLMRequest configuration
        timeout: Timeout in seconds

    Returns:
        Generated text

    Raises:
        HTTPException: On timeout or error
    """
    # Create future for response
    response_future = asyncio.Future()
    response_text = []

    def on_llm_response(data: dict):
        """Callback for LLM response chunks."""
        response_obj = data.get("response")
        if response_obj:
            if hasattr(response_obj, "message"):
                response_text.append(response_obj.message)
            if (
                hasattr(response_obj, "is_end_of_message")
                and response_obj.is_end_of_message
            ):
                if not response_future.done():
                    response_future.set_result("".join(response_text))

    # Register temporary signal handler
    mediator = SignalMediator()
    mediator.register(SignalCode.LLM_TEXT_STREAMED_SIGNAL, on_llm_response)

    try:
        # Send request via signal
        llm_service.send_request(
            prompt=prompt,
            llm_request=llm_request,
            action=LLMActionType.CHAT,
            do_tts_reply=False,  # No TTS for API requests
        )

        # Wait for response (with timeout)
        try:
            response = await asyncio.wait_for(response_future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504, detail="LLM request timed out"
            )

    finally:
        # Unregister signal handler
        mediator.unregister(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL, on_llm_response
        )


# ====================
# API Endpoints
# ====================


@router.post("/chat", response_model=ChatCompletionResponse)
async def chat_completion(request: ChatCompletionRequest, req: Request):
    """
    Chat completion endpoint.

    Args:
        request: Chat completion request
        req: FastAPI request for accessing app state

    Returns:
        Chat completion response
    """
    logger.info(f"Chat completion request: {len(request.messages)} messages")

    llm_service = get_llm_service(req)
    if not llm_service:
        raise HTTPException(
            status_code=503, detail="LLM service not available"
        )

    # Convert messages to prompt (use last message as prompt)
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    prompt = request.messages[-1].content

    # Create LLM request with parameters from API request
    llm_request = LLMRequest.from_default()
    if request.max_tokens:
        llm_request.max_new_tokens = request.max_tokens
        print(
            f"[LLM ROUTE DEBUG] Set max_new_tokens={request.max_tokens} from request.max_tokens",
            flush=True,
        )
    if request.temperature:
        llm_request.temperature = request.temperature

    print(
        f"[LLM ROUTE DEBUG] Final llm_request.max_new_tokens={llm_request.max_new_tokens}",
        flush=True,
    )

    # Wait for response
    response = await wait_for_llm_response(llm_service, prompt, llm_request)

    return ChatCompletionResponse(
        content=response,
        model=request.model or "default",
        finish_reason="stop",
    )


@router.post("/completion", response_model=CompletionResponse)
async def text_completion(request: CompletionRequest, req: Request):
    """
    Text completion endpoint.

    Args:
        request: Completion request
        req: FastAPI request for accessing app state

    Returns:
        Generated text
    """
    logger.info(f"Text completion request: {request.prompt[:50]}...")

    llm_service = get_llm_service(req)
    if not llm_service:
        raise HTTPException(
            status_code=503, detail="LLM service not available"
        )

    # Create LLM request with parameters
    llm_request = LLMRequest.from_default()
    llm_request.max_new_tokens = request.max_tokens
    llm_request.temperature = request.temperature

    # Wait for response
    response = await wait_for_llm_response(
        llm_service, request.prompt, llm_request
    )

    return CompletionResponse(text=response, finish_reason="stop")


@router.get("/models", response_model=List[ModelInfo])
async def list_models(req: Request):
    """
    List available LLM models.

    Args:
        req: FastAPI request for accessing app state

    Returns:
        List of available models
    """
    # Get current model from settings
    settings = LLMGeneratorSettings.objects.first()
    current_model = settings.model_version if settings else None

    # Get available models from ModelRegistry if possible
    try:
        registry = ModelRegistry()
        models = []

        for model_id, model_spec in registry.models.items():
            if model_spec.model_type.value == "llm":
                models.append(
                    ModelInfo(
                        id=model_id,
                        name=model_spec.name,
                        loaded=(model_id == current_model),
                        size_mb=model_spec.size_mb,
                    )
                )

        return models

    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error listing models: {str(e)}"
        )


@router.post("/load")
async def load_model(request: ModelLoadRequest, req: Request):
    """
    Load a specific LLM model.

    Args:
        request: Model load request
        req: FastAPI request for accessing app state

    Returns:
        Success status
    """
    logger.info(f"Load model request: {request.model_id}")

    llm_service = get_llm_service(req)
    if not llm_service:
        raise HTTPException(
            status_code=503, detail="LLM service not available"
        )

    try:
        # Create future for load completion
        load_future = asyncio.Future()

        def on_model_loaded(data: dict):
            if not load_future.done():
                load_future.set_result(True)

        # Register signal handler
        mediator = SignalMediator()
        mediator.register(SignalCode.LLM_LOAD_COMPLETE_SIGNAL, on_model_loaded)

        try:
            # Update settings to use new model
            llm_service.model_changed(request.model_id)

            # Emit load signal
            llm_service.emit_signal(
                SignalCode.LLM_LOAD_SIGNAL, {"model_path": request.model_id}
            )

            # Wait for load to complete (with timeout)
            try:
                await asyncio.wait_for(load_future, timeout=300.0)
            except asyncio.TimeoutError:
                raise HTTPException(
                    status_code=504, detail="Model load timed out"
                )

            return {"status": "success", "model": request.model_id}

        finally:
            mediator.unregister(
                SignalCode.LLM_LOAD_COMPLETE_SIGNAL, on_model_loaded
            )

    except Exception as e:
        logger.error(f"Error loading model: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error loading model: {str(e)}"
        )


@router.post("/unload")
async def unload_model(req: Request):
    """
    Unload current LLM model.

    Args:
        req: FastAPI request for accessing app state

    Returns:
        Success status
    """
    logger.info("Unload model request")

    llm_service = get_llm_service(req)
    if not llm_service:
        raise HTTPException(
            status_code=503, detail="LLM service not available"
        )

    try:

        # Emit unload signal
        llm_service.emit_signal(SignalCode.LLM_UNLOAD_SIGNAL, {})

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error unloading model: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error unloading model: {str(e)}"
        )


@router.websocket("/stream")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat.

    Args:
        websocket: WebSocket connection
    """
    await websocket.accept()
    logger.info("WebSocket connection established")

    try:
        llm_service = LLMAPIService()
        mediator = SignalMediator()

        async def on_llm_chunk(data: dict):
            """Send LLM response chunks to WebSocket client."""
            response_obj = data.get("response")
            if response_obj and hasattr(response_obj, "message"):
                await websocket.send_json(
                    {
                        "type": "chunk",
                        "content": response_obj.message,
                        "done": (
                            hasattr(response_obj, "is_end_of_message")
                            and response_obj.is_end_of_message
                        ),
                    }
                )

        # Register signal handler for streaming
        mediator.register(SignalCode.LLM_TEXT_STREAMED_SIGNAL, on_llm_chunk)

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_json()
                logger.info(f"Received WebSocket message: {data}")

                prompt = data.get("message", "")
                if not prompt:
                    await websocket.send_json(
                        {"type": "error", "content": "No message provided"}
                    )
                    continue

                # Create LLM request
                llm_request = LLMRequest.from_default()
                if "max_tokens" in data:
                    llm_request.max_new_tokens = data["max_tokens"]
                if "temperature" in data:
                    llm_request.temperature = data["temperature"]

                # Send request (response will stream via signal handler)
                llm_service.send_request(
                    prompt=prompt,
                    llm_request=llm_request,
                    action=LLMActionType.CHAT,
                    do_tts_reply=False,
                )

        except WebSocketDisconnect:
            logger.info("WebSocket connection closed")

        finally:
            # Cleanup signal handler
            mediator.unregister(
                SignalCode.LLM_TEXT_STREAMED_SIGNAL, on_llm_chunk
            )

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json(
                {"type": "error", "content": f"Server error: {str(e)}"}
            )
        except:
            pass
