"""
Art generation endpoints (Stable Diffusion).

Integrates with ARTAPIService and JobTracker for asynchronous image generation.
"""

import io
import asyncio
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.utils.job_tracker import JobTracker, JobStatus as JobState
from airunner.components.model_management.model_registry import (
    ModelRegistry,
)
from airunner.components.art.data.generator_settings import (
    GeneratorSettings,
)
from airunner.components.art.api.art_services import ARTAPIService
from airunner.enums import SignalCode
from airunner.utils.application.signal_mediator import SignalMediator
from airunner.enums import SignalCode

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
router = APIRouter()


# ====================
# Pydantic Models
# ====================


class GenerationRequest(BaseModel):
    """Image generation request."""

    prompt: str
    negative_prompt: Optional[str] = ""
    width: int = 1024
    height: int = 1024
    steps: int = 20
    cfg_scale: float = 7.5
    seed: Optional[int] = None
    num_images: int = 1


class GenerationResponse(BaseModel):
    """Image generation response."""

    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    """Generation job status."""

    job_id: str
    status: str
    progress: float
    image_url: Optional[str] = None
    error: Optional[str] = None


class ModelInfo(BaseModel):
    """Model information."""

    id: str
    name: str
    loaded: bool
    type: str  # flux, etc


# ====================
# Helper Functions
# ====================


def get_art_service(request: Request):
    """Get ARTAPIService from FastAPI app state."""
    if hasattr(request.app.state, "airunner_app"):
        return ARTAPIService()
    return None


# ====================
# API Endpoints
# ====================


@router.post("/generate", response_model=GenerationResponse)
async def generate_image(request: GenerationRequest, req: Request):
    """
    Start image generation.

    Args:
        request: Generation parameters
        req: FastAPI request for accessing app state

    Returns:
        Job ID for status checking
    """
    logger.info(f"Image generation request: {request.prompt[:50]}...")

    art_service = get_art_service(req)
    if not art_service:
        raise HTTPException(
            status_code=503, detail="Art service not available"
        )

    try:
        # Create job
        tracker = JobTracker()
        job_id = await tracker.create_job(
            metadata={
                "prompt": request.prompt,
                "negative_prompt": request.negative_prompt,
                "width": request.width,
                "height": request.height,
                "steps": request.steps,
                "cfg_scale": request.cfg_scale,
                "seed": request.seed,
                "num_images": request.num_images,
            }
        )

        # Update job to running
        await tracker.update_progress(job_id, 0.0, JobState.RUNNING)

        # Set up signal handlers
        mediator = SignalMediator()

        def on_image_generated(data: dict):
            """Handle image generation completion."""
            logger.info(f"Image generated for job {job_id}")
            # Store image data in job result
            asyncio.create_task(
                tracker.complete_job(job_id, {"image": data.get("image")})
            )

        def on_generator_progress(data: dict):
            """Handle progress updates."""
            progress = data.get("progress", 0.0)
            asyncio.create_task(tracker.update_progress(job_id, progress))

        def on_error(data: dict):
            """Handle generation errors."""
            error = data.get("message", "Unknown error")
            asyncio.create_task(tracker.fail_job(job_id, error))

        # Register handlers
        mediator.register(
            SignalCode.SD_IMAGE_GENERATED_SIGNAL, on_image_generated
        )
        mediator.register(SignalCode.SD_PROGRESS_SIGNAL, on_generator_progress)
        mediator.register(SignalCode.APPLICATION_ERROR_SIGNAL, on_error)

        # Emit generation request
        art_service.emit_signal(
            SignalCode.SD_GENERATE_IMAGE_SIGNAL,
            {
                "prompt": request.prompt,
                "negative_prompt": request.negative_prompt,
                "width": request.width,
                "height": request.height,
                "steps": request.steps,
                "cfg_scale": request.cfg_scale,
                "seed": request.seed,
                "num_images": request.num_images,
            },
        )

        return GenerationResponse(job_id=job_id, status="running")

    except Exception as e:
        logger.error(f"Error starting generation: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error starting generation: {str(e)}"
        )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Check generation job status.

    Args:
        job_id: Job ID from generate endpoint

    Returns:
        Job status and progress
    """
    logger.debug(f"Status check: {job_id}")

    tracker = JobTracker()
    job = await tracker.get_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress=job.progress,
        image_url=(
            f"/api/v1/art/result/{job_id}"
            if job.status == JobState.COMPLETED
            else None
        ),
        error=job.error,
    )


@router.get("/result/{job_id}")
async def get_result(job_id: str):
    """
    Get generated image.

    Args:
        job_id: Job ID from generate endpoint

    Returns:
        Generated image (PNG)
    """
    logger.info(f"Result retrieval: {job_id}")

    tracker = JobTracker()
    job = await tracker.get_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobState.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed (status: {job.status.value})",
        )

    if not job.result or "image" not in job.result:
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        # Convert PIL Image to PNG bytes
        image = job.result["image"]
        img_io = io.BytesIO()
        image.save(img_io, "PNG")
        img_io.seek(0)

        return StreamingResponse(img_io, media_type="image/png")

    except Exception as e:
        logger.error(f"Error returning image: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error returning image: {str(e)}"
        )


@router.delete("/cancel/{job_id}")
async def cancel_job(job_id: str, req: Request):
    """
    Cancel a generation job.

    Args:
        job_id: Job ID to cancel
        req: FastAPI request for accessing app state

    Returns:
        Success status
    """
    logger.info(f"Cancel job: {job_id}")

    art_service = get_art_service(req)
    if not art_service:
        raise HTTPException(
            status_code=503, detail="Art service not available"
        )

    tracker = JobTracker()
    cancelled = await tracker.cancel_job(job_id)

    if not cancelled:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")

    # Emit interrupt signal
    art_service.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL, {})

    return {"status": "cancelled", "job_id": job_id}


@router.get("/models", response_model=List[ModelInfo])
async def list_models(req: Request):
    """
    List available SD models.

    Args:
        req: FastAPI request for accessing app state

    Returns:
        List of available models
    """
    try:
        # Get current model from settings
        settings = GeneratorSettings.objects.first()
        current_model = settings.model_version if settings else None

        # Get available models from ModelRegistry
        registry = ModelRegistry()
        models = []

        for model_id, model_spec in registry.models.items():
            if model_spec.model_type.value == "flux":
                models.append(
                    ModelInfo(
                        id=model_id,
                        name=model_spec.name,
                        loaded=(model_id == current_model),
                        type=model_spec.model_type.value,
                    )
                )

        return models

    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error listing models: {str(e)}"
        )
