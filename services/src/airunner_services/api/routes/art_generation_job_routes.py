"""Job-status and result routes for art API endpoints."""

import asyncio
import io
import os
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from PIL.Image import Image as PILImage

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.utils.job_tracker import (
    JobStatus as JobState,
    JobTracker,
)

from .art_contracts import JobStatusResponse
from .art_runtime import require_runtime_registry, resolve_art_client

router = APIRouter()
logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
_LOG_ART_STATUS_POLLS = os.environ.get(
    "AIRUNNER_LOG_ART_STATUS_POLLS",
    "0",
) == "1"


# Result and status formatting
# These helpers keep the daemon-facing job protocol in one place so the public
# endpoints can stay readable without changing any response payloads.


async def require_job(job_id: str) -> Any:
    """Return one tracked art job or raise when it does not exist."""
    tracker = JobTracker()
    job = await tracker.get_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def completed_image_url(job_id: str, job: Any) -> Optional[str]:
    """Return the result URL when one job has completed."""
    if job.status == JobState.COMPLETED:
        return f"/api/v1/art/result/{job_id}"
    return None


def status_response(job_id: str, job: Any) -> JobStatusResponse:
    """Build the response payload for one tracked art job."""
    import base64
    import io
    image_b64 = None
    if job.status == JobState.COMPLETED and job.result:
        raw = job.result.get("image_bytes")
        if raw:
            if isinstance(raw, bytes):
                image_b64 = base64.b64encode(raw).decode("ascii")
            else:
                image_b64 = raw
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress=job.progress,
        image_url=completed_image_url(job_id, job),
        image=image_b64,
        error=job.error,
    )


def require_completed_job(job: Any) -> None:
    """Raise when one tracked art job has not completed yet."""
    if job.status != JobState.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed (status: {job.status.value})",
        )


def require_result_payload(job: Any) -> dict:
    """Return the stored result payload for one completed art job."""
    result = job.result or {}
    if not {"image", "image_bytes"}.intersection(result):
        raise HTTPException(status_code=404, detail="Image not found")
    return result


def png_response(result: dict) -> Response:
    """Return one PNG response for a stored art job result."""
    image_bytes = result.get("image_bytes")
    if image_bytes:
        return Response(content=image_bytes, media_type="image/png")
    image = result["image"]
    if not isinstance(image, PILImage):
        raise ValueError("Stored image is not a PIL Image")
    image_io = io.BytesIO()
    image.save(image_io, "PNG")
    return Response(content=image_io.getvalue(), media_type="image/png")


# Status polling, result download, and cancellation share the same tracker
# lookup rules, but they intentionally stay as separate routes so callers keep
# the existing endpoint layout and HTTP semantics.


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Check generation job status and progress."""
    if _LOG_ART_STATUS_POLLS:
        logger.debug("Status check: %s", job_id)
    job = await require_job(job_id)
    return status_response(job_id, job)


@router.get("/result/{job_id}")
async def get_result(job_id: str):
    """Return one generated image as PNG bytes."""
    logger.info("Result retrieval: %s", job_id)
    job = await require_job(job_id)
    require_completed_job(job)
    try:
        return png_response(require_result_payload(job))
    except Exception as exc:
        logger.error("Error returning image: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Error returning image: {exc}",
        ) from exc


@router.delete("/cancel/{job_id}")
async def cancel_job(job_id: str, req: Request):
    """Cancel one generation job and its runtime request."""
    # Cancellation remains best-effort against the runtime because the tracker
    # state is the authoritative source for callers polling this route surface.
    logger.info("Cancel job: %s", job_id)
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