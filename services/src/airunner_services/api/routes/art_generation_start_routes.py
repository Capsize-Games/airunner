"""Generation-start routes for art API endpoints."""

import asyncio
import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.utils.job_tracker import (
    JobStatus as JobState,
    JobTracker,
)

from .art_contracts import GenerationRequest, GenerationResponse
from .art_job_runner import build_generation_job_metadata, run_art_job
from .art_runtime import (
    require_runtime_registry,
    resolve_art_client,
    unload_llm_before_art,
)

router = APIRouter()
logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


# Seed selection stays near the route entry point so callers keep the existing
# request contract while the runtime still receives one explicit seed value.


def resolve_seed_value(seed: Optional[int]) -> int:
    """Return the caller-provided seed or one random reproducible seed."""
    if seed is not None:
        return int(seed)
    return secrets.randbelow(2**31 - 1)


async def _track_art_model(
    tracker: JobTracker,
    job_id: str,
    model_path: str,
    model_version: str,
) -> None:
    """Poll a generation job and update the active-models list.

    Registered as "loading" immediately, then transitions to "loaded"
    once the job completes.
    """
    import os as _os

    from .models_status import (  # noqa: PLC0415
        _external_models,
        _external_models_lock,
        _notify_status_subscribers,
    )

    model_name = _os.path.basename(model_path.rstrip("/")) or model_path

    # Register as loading
    with _external_models_lock:
        _external_models[model_path] = {
            "model_id": model_path,
            "model_type": model_version or "art",
            "status": "loading",
            "can_unload": True,
            "vram_gb": 0.0,
            "ram_gb": 0.0,
            "name": model_name,
        }
    _notify_status_subscribers({
        "type": "model_status",
        "model_type": model_version or "art",
        "model_id": model_path,
        "status": "loading",
    })

    # Poll until the job finishes
    from airunner_services.utils.job_tracker import JobStatus as _JobStatus  # noqa: PLC0415
    terminal_states = {_JobStatus.COMPLETED, _JobStatus.FAILED, _JobStatus.CANCELLED}
    while True:
        job_state = await tracker.get_status(job_id)
        if job_state is None or job_state.status in terminal_states:
            break
        await asyncio.sleep(1)

    loaded = job_state is not None and job_state.status == _JobStatus.COMPLETED
    final_status = "loaded" if loaded else "unloaded"
    with _external_models_lock:
        if loaded:
            _external_models[model_path]["status"] = "loaded"
            _external_models[model_path]["can_unload"] = True
        else:
            _external_models.pop(model_path, None)
    _notify_status_subscribers({
        "type": "model_status",
        "model_type": model_version or "art",
        "model_id": model_path,
        "status": final_status,
    })


async def create_generation_job(
    request: GenerationRequest,
    req: Request,
) -> str:
    """Create one tracked generation job and start its worker task."""
    # Art generation owns its own tracker lifecycle, but it still coordinates
    # with the daemon LLM so image work does not start while VRAM is occupied.
    await unload_llm_before_art(req, source="art_generate")
    client = resolve_art_client(require_runtime_registry(req))
    tracker = JobTracker()
    seed_value = resolve_seed_value(request.seed)
    job_id = await tracker.create_job(
        metadata=build_generation_job_metadata(request, seed_value),
    )
    await tracker.update_progress(job_id, 1.0, JobState.RUNNING)
    art_request = request.model_copy(update={"seed": seed_value})

    # Track the art model in the main daemon's active-models list so it
    # appears in the /api/v1/models/active response even when the model
    # loads in a sidecar process.
    if request.model:
        asyncio.create_task(
            _track_art_model(
                tracker, job_id, request.model, request.version or "",
            ),
        )

    asyncio.create_task(run_art_job(tracker, job_id, art_request, client))
    return job_id


@router.post("/generate", response_model=GenerationResponse)
async def generate_image(request: GenerationRequest, req: Request):
    """Start image generation and return the tracked job id."""
    # The route stays intentionally thin; the helper above owns the tracker,
    # runtime client, and task bootstrap so the API surface remains stable.
    logger.info("Image generation request (prompt_len=%s)", len(request.prompt))
    try:
        job_id = await create_generation_job(request, req)
        return GenerationResponse(job_id=job_id, status="running")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error starting generation: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Error starting generation: {exc}",
        ) from exc