"""Art generation endpoints (Stable Diffusion).

Integrates with ARTAPIService and JobTracker for asynchronous image generation.

NOTE: This module must work in headless/server mode.
The previous implementation waited for SD_* completion signals that are not
emitted in that pipeline, causing jobs to stay RUNNING forever.
"""

import io
import asyncio
import os
import secrets
from pathlib import Path
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from PIL.Image import Image as PILImage

from airunner.settings import (
    AIRUNNER_LOG_LEVEL,
    AIRUNNER_ART_MODEL_PATH,
    AIRUNNER_ART_MODEL_VERSION,
    AIRUNNER_ART_SCHEDULER,
)
from airunner.utils.application import get_logger
from airunner.utils.job_tracker import JobTracker, JobStatus as JobState
from airunner.components.model_management.model_registry import (
    ModelRegistry,
    ModelType as RegistryModelType,
    ModelProvider,
)
from airunner.components.art.data.generator_settings import (
    GeneratorSettings,
)
from airunner.components.settings.data.path_settings import PathSettings
from airunner.components.art.api.art_services import ARTAPIService
from airunner.components.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner.enums import GeneratorSection, SignalCode, StableDiffusionVersion

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


class LocalArtModel(BaseModel):
    id: str
    name: str
    path: str
    size_bytes: int


class LocalArtModelsResponse(BaseModel):
    base_dir: str
    models: List[LocalArtModel]


# ====================
# Helper Functions
# ====================


def get_art_service(request: Request):
    """Get an object that can emit signals to the shared worker graph.

    Important: emitting signals on a *fresh* ARTAPIService() creates a new
    SignalMediator with no workers registered, so generation never starts.
    """
    airunner_app = getattr(request.app.state, "airunner_app", None)
    if airunner_app is None:
        return None
    if not hasattr(airunner_app, "emit_signal"):
        return None
    return airunner_app


def _resolve_art_model_path(model_version: Optional[str] = None) -> str:
    """Resolve the art model identifier/path.

    Priority:
    1) AIRUNNER_ART_MODEL_PATH env
    2) GeneratorSettings.custom_path
    3) GeneratorSettings.aimodel.path
    4) First local model found under {base_path}/art/models/{version}/{pipeline_action}

    Notes:
    - In our headless worker pipeline, model_path is treated as a filesystem
      path (file or directory). Passing a HuggingFace ID here will be treated
      as "path does not exist" and generation will stall.
    """
    configured = (AIRUNNER_ART_MODEL_PATH or "").strip()
    if configured:
        try:
            if Path(configured).expanduser().exists():
                return configured
        except Exception:
            pass
        return ""

    def _choose_from_action_dir(action_dir: Path) -> str:
        # Prefer diffusers-style directory (presence of model_index.json).
        try:
            if (action_dir / "model_index.json").exists():
                return str(action_dir)
        except Exception:
            pass

        for ext in (".safetensors", ".ckpt", ".gguf"):
            try:
                candidates = sorted(action_dir.glob(f"*{ext}"))
                if candidates:
                    return str(candidates[0])
            except Exception:
                continue
        return ""

    try:
        from airunner.components.data.session_manager import session_scope

        with session_scope() as session:
            path_settings = session.query(PathSettings).first()
            base_path = (
                (getattr(path_settings, "base_path", "") or "").strip()
                if path_settings is not None
                else ""
            )
            base_path = base_path or os.path.expanduser(
                os.path.join("~", ".local", "share", "airunner")
            )
            model_base = Path(base_path).expanduser() / "art" / "models"

            settings = session.query(GeneratorSettings).first()

            if settings is not None:
                custom_path = (getattr(settings, "custom_path", "") or "").strip()
                if custom_path and Path(custom_path).expanduser().exists():
                    return custom_path

            # Prefer the caller-provided version (e.g., resolved from local models)
            # so we don't accidentally mix a default version (Flux) with a Z-Image model path.
            version = (model_version or "").strip()
            action = "txt2img"
            if settings is not None:
                action = (getattr(settings, "pipeline_action", "") or "").strip() or action

            if version:
                action_dir = model_base / version / action
                if action_dir.exists():
                    chosen = _choose_from_action_dir(action_dir)
                    if chosen:
                        return chosen

                # Some installs store models directly under the version dir.
                version_dir = model_base / version
                if version_dir.exists():
                    for maybe_action in sorted(
                        p for p in version_dir.iterdir() if p.is_dir()
                    ):
                        chosen = _choose_from_action_dir(maybe_action)
                        if chosen:
                            return chosen

            # Last resort: pick the first model under the model base path.
            if model_base.exists():
                for version_dir in sorted(p for p in model_base.iterdir() if p.is_dir()):
                    for action_dir in sorted(p for p in version_dir.iterdir() if p.is_dir()):
                        chosen = _choose_from_action_dir(action_dir)
                        if chosen:
                            return chosen
    except Exception:
        pass

    return ""


def _resolve_art_model_version() -> str:
    configured = (AIRUNNER_ART_MODEL_VERSION or "").strip()
    if configured:
        return configured

    # Determine model base directory for validation + auto-detection.
    # This avoids defaulting to Flux when only SDXL/Z-Image models are installed.
    try:
        from airunner.components.data.session_manager import session_scope

        with session_scope() as session:
            path_settings = session.query(PathSettings).first()
            base_path = (
                (getattr(path_settings, "base_path", "") or "").strip()
                if path_settings is not None
                else ""
            )
    except Exception:
        base_path = ""

    base_path = base_path or os.path.expanduser(
        os.path.join("~", ".local", "share", "airunner")
    )
    model_base = Path(base_path).expanduser() / "art" / "models"

    # Prefer a DB-configured version only if it's actually available locally.
    try:
        from airunner.components.data.session_manager import session_scope

        with session_scope() as session:
            settings = session.query(GeneratorSettings).first()
            if settings is not None:
                version = (getattr(settings, "version", "") or "").strip()
                if version and (model_base / version).exists():
                    return version
    except Exception:
        pass

    preferred_versions = [
        StableDiffusionVersion.Z_IMAGE_TURBO.value,
        StableDiffusionVersion.SDXL1_0.value,
        StableDiffusionVersion.FLUX_SCHNELL.value,
        StableDiffusionVersion.FLUX_DEV.value,
    ]

    def _has_any_pipeline(version_dir: Path) -> bool:
        for action in ("txt2img", "img2img", "inpaint", "outpaint"):
            if (version_dir / action).exists():
                return True
        return False

    if model_base.exists():
        for version in preferred_versions:
            version_dir = model_base / version
            if version_dir.exists() and _has_any_pipeline(version_dir):
                return version

        # Fallback: first folder that looks like a model version.
        known_values = {v.value for v in StableDiffusionVersion}
        for version_dir in sorted(p for p in model_base.iterdir() if p.is_dir()):
            if version_dir.name in known_values and _has_any_pipeline(version_dir):
                return version_dir.name

    return StableDiffusionVersion.Z_IMAGE_TURBO.value


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
    logger.info(f"Image generation request (prompt_len={len(request.prompt)})")

    # Ensure the app instance exists so signals route to workers.
    art_service = get_art_service(req)
    if not art_service:
        raise HTTPException(
            status_code=503, detail="Art service not available"
        )

    # Ensure SD is enabled in headless mode.
    if os.environ.get("AIRUNNER_SD_ON") != "1":
        raise HTTPException(
            status_code=503,
            detail="Stable Diffusion service is not enabled (AIRUNNER_SD_ON!=1)",
        )

    model_version = _resolve_art_model_version()

    model_path = _resolve_art_model_path(model_version=model_version)
    if not model_path:
        raise HTTPException(
            status_code=503,
            detail=(
                "No local art model could be resolved. Set AIRUNNER_ART_MODEL_PATH to an existing local file/dir (or ensure ~/.local/share/airunner/art/models contains a model)."
            ),
        )

    logger.info("Resolved art model: version=%s path=%s", model_version, model_path)

    # Important: historically, we treated a blank seed as "random" but still
    # passed a constant default seed (42) into the worker request. Some worker
    # paths effectively use that value even when random_seed=True, producing the
    # same image repeatedly.
    #
    # If the caller did not provide a seed, pick one here so each request is
    # reproducible (if needed) but different across requests.
    seed_value = int(request.seed) if request.seed is not None else secrets.randbelow(2**31 - 1)

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
                "seed": seed_value,
                "num_images": request.num_images,
            }
        )

        # Update job to running
        await tracker.update_progress(job_id, 0.0, JobState.RUNNING)

        # Use the callback-based generation path.
        # This works in headless/server mode and avoids global signal handlers
        # that would otherwise leak and/or never fire.
        loop = asyncio.get_running_loop()

        def _complete_job_from_thread(image: PILImage):
            fut = asyncio.run_coroutine_threadsafe(
                tracker.complete_job(job_id, {"image": image}),
                loop,
            )
            try:
                fut.result(timeout=10)
            except FutureTimeoutError:
                logger.warning(
                    "Job completion timed out while scheduling job_id=%s",
                    job_id,
                )

        def _fail_job_from_thread(error: str):
            fut = asyncio.run_coroutine_threadsafe(
                tracker.fail_job(job_id, error),
                loop,
            )
            try:
                fut.result(timeout=10)
            except FutureTimeoutError:
                logger.warning(
                    "Job failure timed out while scheduling job_id=%s",
                    job_id,
                )

        def on_complete(response):
            try:
                if isinstance(response, str):
                    _fail_job_from_thread(response)
                    return

                images = None
                if isinstance(response, ImageResponse):
                    images = response.images
                elif isinstance(response, dict):
                    images = response.get("images")

                if not images or images[0] is None:
                    _fail_job_from_thread("No image returned")
                    return

                _complete_job_from_thread(images[0])
            except Exception as exc:
                _fail_job_from_thread(str(exc))

        image_request = ImageRequest(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt or "",
            width=request.width,
            height=request.height,
            steps=request.steps,
            scale=request.cfg_scale,
            random_seed=False,
            seed=seed_value,
            n_samples=request.num_images,
            images_per_batch=request.num_images,
            generator_section=GeneratorSection.TXT2IMG,
            model_path=model_path,
            version=model_version,
        )
        if AIRUNNER_ART_SCHEDULER:
            image_request.scheduler = AIRUNNER_ART_SCHEDULER

        image_request.callback = on_complete

        art_service.emit_signal(
            SignalCode.DO_GENERATE_SIGNAL,
            {"image_request": image_request},
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
        if not isinstance(image, PILImage):
            raise ValueError("Stored image is not a PIL Image")

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


def _resolve_zimage_txt2img_dir() -> str:
    """Return the txt2img directory for Z-Image models inside the container."""
    try:
        from airunner.components.data.session_manager import session_scope

        with session_scope() as session:
            path_settings = session.query(PathSettings).first()
            base_path = (
                (getattr(path_settings, "base_path", "") or "").strip()
                if path_settings is not None
                else ""
            )
    except Exception:
        base_path = ""

    # PathSettings is the source of truth in headless mode.
    base_path = base_path or os.path.expanduser(os.path.join("~", ".local", "share", "airunner"))

    candidates = [
        str(Path(base_path).expanduser() / "art" / "models" / "Z-Image Turbo" / "txt2img"),
        # Common bind mounts used in some dev compose stacks.
        "/home/airunner/.local/share/airunner/art/models/Z-Image Turbo/txt2img",
        "/home/joe/.local/share/airunner/art/models/Z-Image Turbo/txt2img",
    ]
    for d in candidates:
        try:
            if Path(d).expanduser().is_dir():
                return str(Path(d).expanduser())
        except Exception:
            continue
    return ""


@router.get("/models", response_model=LocalArtModelsResponse)
async def list_models(req: Request):
    """List local checkpoint files suitable for txt2img (e.g., Z-Image safetensors)."""
    base_dir = _resolve_zimage_txt2img_dir()
    models: list[LocalArtModel] = []

    if base_dir:
        for p in sorted(Path(base_dir).glob("*.safetensors")):
            try:
                st = p.stat()
                models.append(
                    LocalArtModel(
                        id=str(p),
                        name=p.name,
                        path=str(p),
                        size_bytes=int(st.st_size),
                    )
                )
            except Exception:
                continue

    return LocalArtModelsResponse(base_dir=base_dir, models=models)


@router.get("/models/registry", response_model=List[ModelInfo])
async def list_registry_models(req: Request):
    """List models from AIRunner's internal ModelRegistry (HF IDs)."""
    registry = ModelRegistry()
    candidates = registry.list_models(
        provider=ModelProvider.STABLE_DIFFUSION,
        model_type=RegistryModelType.TEXT_TO_IMAGE,
    )

    configured = _resolve_art_model_path()
    return [
        ModelInfo(
            id=m.huggingface_id,
            name=m.name,
            loaded=(bool(configured) and configured == m.huggingface_id),
            type=m.model_type.value,
        )
        for m in candidates
    ]
