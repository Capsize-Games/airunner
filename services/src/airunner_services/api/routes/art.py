"""Art generation endpoints (Stable Diffusion).

Routes art generation through the daemon runtime registry.

NOTE: This module must work in headless/server mode.
"""

import base64
import io
import asyncio
import os
import secrets
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from PIL.Image import Image as PILImage

from airunner_services.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import (
    ArtInvocationRequest,
    RuntimeAction,
    RuntimeKind,
    RuntimeMode,
)
from airunner_services.runtimes.registry import RuntimeRegistry, RuntimeRoute
from airunner_services.settings import (
    AIRUNNER_LOG_LEVEL,
    AIRUNNER_ART_MODEL_PATH,
    AIRUNNER_ART_MODEL_VERSION,
)
from airunner_services.utils.application import get_logger
from airunner_services.utils.job_tracker import (
    JobStatus as JobState,
    JobTracker,
)
from airunner_services.model_management.model_registry import (
    ModelRegistry,
    ModelType as RegistryModelType,
    ModelProvider,
)
from airunner_model.models.generator_settings import (
    GeneratorSettings,
)
from airunner_model.models.path_settings import PathSettings
from airunner_services.contract_enums import ModelStatus
from airunner_services.contract_enums import StableDiffusionVersion

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
router = APIRouter()
_LOG_ART_STATUS_POLLS = os.environ.get(
    "AIRUNNER_LOG_ART_STATUS_POLLS",
    "0",
) == "1"
_LLM_ART_BUSY_STATUSES = frozenset(
    {
        ModelStatus.LOADING,
        ModelStatus.LOADED,
        ModelStatus.READY,
    }
)
_LLM_UNLOAD_TIMEOUT_SECONDS = 30.0
_LLM_UNLOAD_POLL_SECONDS = 0.1


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
    model: Optional[str] = None
    version: Optional[str] = None
    scheduler: Optional[str] = None
    pipeline: Optional[str] = None
    strength: Optional[float] = None
    image_b64: Optional[str] = None
    skip_auto_export: bool = False


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
    type: str  # zimage, stablediffusion, etc


class LocalArtModel(BaseModel):
    id: str
    name: str
    path: str
    size_bytes: int


class LocalArtModelsResponse(BaseModel):
    base_dir: str
    models: List[LocalArtModel]


class BackgroundRemovalRequest(BaseModel):
    """Background-removal request payload."""

    image_b64: str


class ArtComponentResponse(BaseModel):
    """Art component control response."""

    component: str
    status: str


# ====================
# Helper Functions
# ====================


def get_runtime_registry(request: Request) -> Optional[RuntimeRegistry]:
    """Return the runtime registry attached to the FastAPI app."""
    return getattr(request.app.state, "runtime_registry", None)


def require_runtime_registry(request: Request) -> RuntimeRegistry:
    """Return the runtime registry or raise when it is unavailable."""
    runtime_registry = get_runtime_registry(request)
    if runtime_registry is None:
        raise HTTPException(status_code=503, detail="Art runtime unavailable")
    return runtime_registry


def resolve_art_client(registry: RuntimeRegistry) -> RuntimeClient:
    """Resolve the art runtime client for the current daemon role."""
    if os.environ.get("AIRUNNER_ART_SIDECAR_PROCESS") == "1":
        route = RuntimeRoute(
            RuntimeKind.ART,
            provider="local",
            deployment_mode=RuntimeMode.LOCAL_FALLBACK.value,
        )
        detail = "Art runtime unavailable"
    else:
        route = RuntimeRoute(
            RuntimeKind.ART,
            provider="local",
            deployment_mode=RuntimeMode.SIDECAR.value,
        )
        detail = "Art sidecar runtime unavailable"

    if not _has_runtime_route(registry, route):
        raise HTTPException(status_code=503, detail=detail)

    client = registry.resolve(
        route.runtime,
        provider=route.provider,
        deployment_mode=route.deployment_mode,
    )
    logger.debug(
        "Resolved art runtime route=%s client=%s",
        route.deployment_mode,
        type(client).__name__,
    )
    return client


def _current_llm_status(req: Request) -> Optional[ModelStatus]:
    """Return the current daemon-owned LLM status when available."""
    lifecycle_service = getattr(req.app.state, "lifecycle_service", None)
    status_getter = getattr(
        lifecycle_service,
        "current_llm_model_status",
        None,
    )
    if not callable(status_getter):
        return None
    try:
        return status_getter()
    except Exception:
        logger.debug(
            "Failed to read LLM status before art request",
            exc_info=True,
        )
        return None


def _llm_blocks_art(req: Request) -> bool:
    """Return True when the daemon still has an active LLM in VRAM."""
    return _current_llm_status(req) in _LLM_ART_BUSY_STATUSES


async def _wait_for_llm_unload(req: Request) -> bool:
    """Wait briefly for the daemon LLM unload to complete."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + _LLM_UNLOAD_TIMEOUT_SECONDS
    while _llm_blocks_art(req):
        if loop.time() >= deadline:
            return False
        await asyncio.sleep(_LLM_UNLOAD_POLL_SECONDS)
    return True


async def _invoke_art_control(
    req: Request,
    *,
    action: RuntimeAction,
    component: Optional[str] = None,
    payload: Optional[dict] = None,
    metadata: Optional[dict] = None,
):
    """Invoke one non-job art runtime request."""
    if action in (RuntimeAction.INVOKE, RuntimeAction.LOAD_MODEL):
        await _unload_llm_before_art(
            req,
            source=f"art_{action.value}",
        )

    request_metadata = dict(metadata or {})
    if component is not None:
        request_metadata["component"] = component

    client = resolve_art_client(require_runtime_registry(req))
    response = await asyncio.to_thread(
        client.invoke,
        RequestEnvelope(
            request_id=secrets.token_urlsafe(12),
            runtime=RuntimeKind.ART,
            action=action,
            payload=payload or {},
            metadata=request_metadata,
        ),
    )
    if response.status is EnvelopeStatus.SUCCEEDED:
        return response

    error = getattr(response, "error", None)
    detail = getattr(error, "message", None) or "Art runtime request failed"
    raise HTTPException(status_code=500, detail=detail)


def _has_runtime_route(registry: RuntimeRegistry, route: RuntimeRoute) -> bool:
    """Return True when one exact runtime route is registered."""
    has_route = getattr(registry, "has_route", None)
    if callable(has_route):
        return bool(has_route(route))
    list_routes = getattr(registry, "list_routes", None)
    if callable(list_routes):
        normalized = route.normalized()
        return any(candidate.normalized() == normalized for candidate in list_routes())
    try:
        registry.resolve(
            route.runtime,
            provider=route.provider,
            deployment_mode=route.deployment_mode,
        )
    except KeyError:
        return False
    return True


async def _job_cancelled(tracker: JobTracker, job_id: str) -> bool:
    """Return True when the tracked art job has already been cancelled."""
    job = await tracker.get_status(job_id)
    return bool(job is not None and job.status is JobState.CANCELLED)


async def _fail_art_job(
    tracker: JobTracker,
    job_id: str,
    message: str,
) -> None:
    """Fail one art job unless it has already been cancelled."""
    if await _job_cancelled(tracker, job_id):
        return
    await tracker.fail_job(job_id, message)


async def _run_art_job(
    tracker: JobTracker,
    job_id: str,
    request: GenerationRequest,
    client: RuntimeClient,
) -> None:
    """Execute one art runtime request and store the JobTracker result."""
    metadata = {}
    if request.version:
        metadata["version"] = request.version
    if request.scheduler:
        metadata["scheduler"] = request.scheduler
    if request.pipeline:
        metadata["pipeline"] = request.pipeline
    if request.strength is not None:
        metadata["strength"] = float(request.strength)
    if request.image_b64:
        metadata["image_b64"] = request.image_b64
    if request.skip_auto_export:
        metadata["skip_auto_export"] = True
    loop = asyncio.get_running_loop()
    envelope = RequestEnvelope(
        request_id=job_id,
        runtime=RuntimeKind.ART,
        action=RuntimeAction.INVOKE,
        provider="local",
        payload=ArtInvocationRequest(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt or "",
            model=request.model,
            width=request.width,
            height=request.height,
            steps=request.steps,
            cfg_scale=request.cfg_scale,
            seed=request.seed,
            num_images=request.num_images,
            metadata=metadata,
        ).model_dump(),
    )

    def on_progress(progress_data: dict) -> None:
        progress = _coerce_job_progress(progress_data)
        if progress is None:
            return
        asyncio.run_coroutine_threadsafe(
            tracker.update_progress(job_id, progress, JobState.RUNNING),
            loop,
        )

    try:
        invoke_with_progress = getattr(client, "invoke_with_progress", None)
        if callable(invoke_with_progress):
            response = await asyncio.to_thread(
                invoke_with_progress,
                envelope,
                on_progress,
            )
        else:
            response = await asyncio.to_thread(client.invoke, envelope)
    except Exception as exc:
        await _fail_art_job(tracker, job_id, str(exc))
        return

    if response.status is EnvelopeStatus.CANCELLED:
        await tracker.cancel_job(job_id)
        return
    if response.status is EnvelopeStatus.FAILED:
        detail = response.error.message if response.error else "Art generation failed"
        await _fail_art_job(tracker, job_id, detail)
        return

    images = (response.payload or {}).get("images") or []
    if not images:
        await _fail_art_job(tracker, job_id, "Art runtime returned no images")
        return

    try:
        image_bytes = base64.b64decode(images[0])
    except Exception as exc:
        await _fail_art_job(tracker, job_id, f"Invalid image payload: {exc}")
        return

    if await _job_cancelled(tracker, job_id):
        return
    await tracker.complete_job(
        job_id,
        {"image_bytes": image_bytes},
    )


def _coerce_job_progress(progress_data: dict) -> Optional[float]:
    """Return one normalized job progress percentage."""
    try:
        progress = float(progress_data.get("progress"))
    except (TypeError, ValueError):
        return None
    return max(0.0, min(99.0, progress))


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
        from airunner_model.session import session_scope

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
            # so we don't accidentally mix a default version with a different model path.
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
    # This avoids defaulting to an unavailable model when only local art
    # models are installed.
    try:
        from airunner_model.session import session_scope

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
        from airunner_model.session import session_scope

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



async def _unload_llm_before_art(
    req: Request,
    source: str = "art_request",
) -> None:
    """Release daemon-owned LLM VRAM before starting art work."""
    if not _llm_blocks_art(req):
        return

    lifecycle_service = getattr(req.app.state, "lifecycle_service", None)
    queue_unload = getattr(lifecycle_service, "queue_llm_unload", None)
    if not callable(queue_unload):
        raise HTTPException(
            status_code=503,
            detail="LLM runtime could not be unloaded for art",
        )

    logger.info("Queueing LLM unload before art request")
    if not bool(queue_unload(source=source)):
        raise HTTPException(
            status_code=503,
            detail="LLM runtime could not be unloaded for art",
        )

    if await _wait_for_llm_unload(req):
        logger.info("LLM unload completed before art request")
        return

    raise HTTPException(
        status_code=503,
        detail="Timed out waiting for LLM unload before art",
    )


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

    # Important: historically, we treated a blank seed as "random" but still
    # passed a constant default seed (42) into the worker request. Some worker
    # paths effectively use that value even when random_seed=True, producing the
    # same image repeatedly.
    #
    # If the caller did not provide a seed, pick one here so each request is
    # reproducible (if needed) but different across requests.
    seed_value = int(request.seed) if request.seed is not None else secrets.randbelow(2**31 - 1)

    try:
        await _unload_llm_before_art(req, source="art_generate")
        client = resolve_art_client(require_runtime_registry(req))
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
                "model": request.model,
                "version": request.version,
                "scheduler": request.scheduler,
            }
        )

        # Update job to running
        await tracker.update_progress(job_id, 1.0, JobState.RUNNING)
        asyncio.create_task(
            _run_art_job(
                tracker,
                job_id,
                request.model_copy(update={"seed": seed_value}),
                client,
            )
        )

        return GenerationResponse(job_id=job_id, status="running")

    except HTTPException:
        raise
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
    if _LOG_ART_STATUS_POLLS:
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

    if not job.result or not {
        "image",
        "image_bytes",
    }.intersection(job.result):
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        image_bytes = job.result.get("image_bytes")
        if image_bytes:
            return Response(content=image_bytes, media_type="image/png")

        # Convert PIL Image to PNG bytes
        image = job.result["image"]
        if not isinstance(image, PILImage):
            raise ValueError("Stored image is not a PIL Image")

        img_io = io.BytesIO()
        image.save(img_io, "PNG")
        return Response(content=img_io.getvalue(), media_type="image/png")

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
    client = resolve_art_client(require_runtime_registry(req))
    tracker = JobTracker()
    cancelled = await tracker.cancel_job(job_id)

    if not cancelled:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")

    try:
        await asyncio.to_thread(client.cancel, job_id)
    except Exception:
        pass

    return {"status": "cancelled", "job_id": job_id}


@router.post("/remove-background")
async def remove_background(
    request: BackgroundRemovalRequest,
    req: Request,
):
    """Remove the background from one input image through the art runtime."""
    response = await _invoke_art_control(
        req,
        action=RuntimeAction.INVOKE,
        payload={
            "prompt": "",
            "metadata": {"image_b64": request.image_b64},
        },
        metadata={"operation": "remove_background"},
    )

    images = response.payload.get("images") or []
    if not images:
        raise HTTPException(
            status_code=500,
            detail="Background removal produced no image output",
        )

    try:
        png_bytes = base64.b64decode(images[0])
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid background removal payload: {exc}",
        ) from exc

    return Response(content=png_bytes, media_type="image/png")


@router.post(
    "/components/{component}/load",
    response_model=ArtComponentResponse,
)
async def load_art_component(component: str, req: Request):
    """Load one explicit art component through the runtime contract."""
    await _invoke_art_control(
        req,
        action=RuntimeAction.LOAD_MODEL,
        component=component,
    )
    return ArtComponentResponse(component=component, status="loaded")


@router.delete(
    "/components/{component}/unload",
    response_model=ArtComponentResponse,
)
async def unload_art_component(component: str, req: Request):
    """Unload one explicit art component through the runtime contract."""
    await _invoke_art_control(
        req,
        action=RuntimeAction.UNLOAD_MODEL,
        component=component,
    )
    return ArtComponentResponse(component=component, status="unloaded")


def _resolve_zimage_txt2img_dir() -> str:
    """Return the txt2img directory for Z-Image models inside the container."""
    try:
        from airunner_model.session import session_scope

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
