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