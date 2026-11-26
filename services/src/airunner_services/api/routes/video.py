"""Video generation endpoints (LTX-2.3). Mirrors /api/v1/art."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from airunner_services.video.contracts import VideoGenerationRequest
from airunner_services.video.pipeline import WeightsMissingError
from airunner_services.video.service import (
    JobNotFoundError,
    QueueFullError,
    VideoService,
)

router = APIRouter()
_service: VideoService | None = None


def get_service() -> VideoService:
    """Return the process-wide video service (built lazily)."""
    global _service
    if _service is None:
        _service = VideoService()
    return _service


def set_service(service: VideoService | None) -> None:
    """Inject a service in tests; None restores lazy building."""
    global _service
    _service = service


@router.post("/generate", status_code=202)
async def generate(request: VideoGenerationRequest) -> dict:
    """Validate + enqueue a clip; returns {job_id} immediately."""
    try:
        job_id = get_service().submit(request)
    except QueueFullError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except WeightsMissingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"job_id": job_id, "status": "queued"}


@router.get("/status/{job_id}")
async def status(job_id: str) -> dict:
    """Return progress + telemetry for one job."""
    try:
        return get_service().status(job_id).model_dump()
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="unknown job") from exc


@router.get("/result/{job_id}")
async def result(job_id: str) -> FileResponse:
    """Return the finished MP4; 409 while not completed."""
    try:
        path = get_service().result_path(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="unknown job") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return FileResponse(path, media_type="video/mp4",
                        filename=f"{job_id}.mp4")


@router.delete("/cancel/{job_id}")
async def cancel(job_id: str) -> dict:
    """Cancel a queued/running job (best-effort)."""
    try:
        return get_service().cancel(job_id).model_dump()
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="unknown job") from exc


@router.get("/models")
async def models() -> dict:
    """List checkpoints with install state and VRAM estimates."""
    return {"models": [m.model_dump() for m in get_service().list_models()]}
