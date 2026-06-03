"""Download job endpoints for service-owned model acquisition."""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import os
import time
from typing import Any

from PIL import Image as PILImage

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from airunner_services.url_safety import safe_fetch_bytes

from airunner_services.downloads.service import (
    fetch_civitai_browser_model_info,
    fetch_civitai_model_info as fetch_civitai_model_info_service,
    search_civitai_models,
)
from airunner_services.downloads.job_service import DownloadJobService

from .downloads_models import (
    CivitaiBrowserModelRequest,
    CivitaiBrowserSearchRequest,
    CivitaiFileDownloadRequest,
    CivitaiImageRequest,
    CivitaiModelInfoRequest,
    DownloadJobAcceptedResponse,
    DownloadJobStatusResponse,
    HuggingFaceDownloadRequest,
    HuggingFaceFileDownloadRequest,
    NltkDownloadRequest,
    UrlDownloadRequest,
)

from airunner_services.downloads.civitai import _BASE_MODEL_ALIASES, _MODEL_TYPE_ALIASES

router = APIRouter()
logger = logging.getLogger(__name__)


def get_download_job_service(request: Request) -> DownloadJobService:
    """Return the process-wide download job service for the API app."""
    service = getattr(request.app.state, "download_job_service", None)
    if service is None:
        service = DownloadJobService()
        request.app.state.download_job_service = service
    return service


@router.post(
    "/huggingface",
    response_model=DownloadJobAcceptedResponse,
)
async def start_huggingface_download(
    payload: HuggingFaceDownloadRequest,
    request: Request,
) -> DownloadJobAcceptedResponse:
    """Queue one HuggingFace download through the shared job service."""
    service = get_download_job_service(request)
    job_id = await service.start_huggingface_download(
        repo_id=payload.repo_id,
        model_type=payload.model_type,
        output_dir=payload.output_dir,
        missing_files=payload.missing_files,
        gguf_filename=payload.gguf_filename,
        prefer_pre_quantized=payload.prefer_pre_quantized,
    )
    return DownloadJobAcceptedResponse(job_id=job_id)


@router.post(
    "/huggingface/file",
    response_model=DownloadJobAcceptedResponse,
)
async def start_huggingface_file_download(
    payload: HuggingFaceFileDownloadRequest,
    request: Request,
) -> DownloadJobAcceptedResponse:
    """Queue one single-file HuggingFace download job."""
    service = get_download_job_service(request)
    job_id = await service.start_huggingface_file_download(
        payload.repo_id,
        payload.filename,
        output_dir=payload.output_dir,
    )
    return DownloadJobAcceptedResponse(job_id=job_id)


@router.post(
    "/url",
    response_model=DownloadJobAcceptedResponse,
)
async def start_url_download(
    payload: UrlDownloadRequest,
    request: Request,
) -> DownloadJobAcceptedResponse:
    """Queue one generic URL download through the shared job service."""
    service = get_download_job_service(request)
    job_id = await service.start_url_download(
        payload.url,
        output_dir=payload.output_dir,
        filename=payload.filename,
        extract_zip=payload.extract_zip,
    )
    return DownloadJobAcceptedResponse(job_id=job_id)


@router.post(
    "/nltk",
    response_model=DownloadJobAcceptedResponse,
)
async def start_nltk_download(
    payload: NltkDownloadRequest,
    request: Request,
) -> DownloadJobAcceptedResponse:
    """Queue one NLTK data download through the shared job service."""
    service = get_download_job_service(request)
    job_id = await service.start_nltk_download(payload.data_names)
    return DownloadJobAcceptedResponse(job_id=job_id)


@router.post(
    "/civitai/file",
    response_model=DownloadJobAcceptedResponse,
)
async def start_civitai_file_download(
    payload: CivitaiFileDownloadRequest,
    request: Request,
) -> DownloadJobAcceptedResponse:
    """Queue one single-file CivitAI download job."""
    service = get_download_job_service(request)
    job_id = await service.start_civitai_file_download(
        payload.url,
        output_path=payload.output_path,
        file_size=payload.file_size,
        api_key=payload.api_key,
    )
    return DownloadJobAcceptedResponse(job_id=job_id)


@router.post("/civitai/info")
async def fetch_civitai_model_info_route(
    payload: CivitaiModelInfoRequest,
) -> dict[str, Any]:
    """Return one selected-version-aware CivitAI model payload."""
    return await asyncio.to_thread(
        fetch_civitai_model_info_service,
        payload.url,
        payload.api_key or "",
    )


@router.get("/civitai/options")
async def civitai_browser_options() -> dict[str, Any]:
    """Return available base-model and model-type filter options.

    These come from the backend's CivitAI integration so the frontend
    never needs to hardcode filter values.
    """
    base_models: list[dict[str, str]] = []
    seen = set()
    for label in _BASE_MODEL_ALIASES:
        value = _BASE_MODEL_ALIASES[label]
        if value not in seen:
            seen.add(value)
            base_models.append({"label": label, "value": value})

    model_types: set[str] = set()
    for value in _MODEL_TYPE_ALIASES.values():
        if value not in ("Checkpoint", "LORA", "TextualInversion"):
            continue
        model_types.add(value)

    return {
        "base_models": base_models,
        "model_types": sorted(model_types),
        "model_types_by_base": {
            bm["value"]: list(model_types) for bm in base_models
        },
    }


@router.post("/civitai/models")
async def search_civitai_models_route(
    payload: CivitaiBrowserSearchRequest,
) -> dict[str, Any]:
    """Return one filtered CivitAI browser search payload."""
    return await asyncio.to_thread(
        search_civitai_models,
        payload.query,
        base_models=payload.base_models,
        model_types=payload.model_types,
        limit=payload.limit,
        cursor=payload.cursor,
        api_key=payload.api_key or "",
    )


@router.post("/civitai/model")
async def fetch_civitai_browser_model_route(
    payload: CivitaiBrowserModelRequest,
) -> dict[str, Any]:
    """Return one filtered CivitAI browser detail payload."""
    try:
        return await asyncio.to_thread(
            fetch_civitai_browser_model_info,
            payload.model_id,
            base_models=payload.base_models,
            model_types=payload.model_types,
            api_key=payload.api_key or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


import threading


# Rate limiter: CivitAI free tier ~10 req/s, be conservative at 5 req/s
_image_fetch_lock = threading.Lock()
_image_fetch_timestamps: list[float] = []
_IMAGE_MAX_RATE = 5  # max requests per second


def _rate_limit_image_fetch() -> None:
    """Block until a CivitAI image fetch is allowed (5 req/s limit)."""
    global _image_fetch_timestamps
    now = time.time()
    with _image_fetch_lock:
        # Prune timestamps older than 1 second
        _image_fetch_timestamps = [
            t for t in _image_fetch_timestamps if now - t < 1.0
        ]
        if len(_image_fetch_timestamps) >= _IMAGE_MAX_RATE:
            # Sleep until oldest timestamp expires
            sleep_for = 1.0 - (now - _image_fetch_timestamps[0])
            if sleep_for > 0:
                time.sleep(sleep_for)
        _image_fetch_timestamps.append(time.time())


# Disk cache for CivitAI preview images (keyed by URL+width)
_IMAGE_CACHE_DIR = os.path.join(
    "/tmp", "airunner", "civitai_image_cache",
)
_IMAGE_CACHE_MAX_AGE = 86400  # 24 hours


def _image_cache_path(url: str, width: int | None) -> str:
    """Return one deterministic cache path for a CivitAI image."""
    raw = f"{url}:{width or 'full'}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    os.makedirs(_IMAGE_CACHE_DIR, exist_ok=True)
    return os.path.join(_IMAGE_CACHE_DIR, f"{digest}.jpg")


def _image_from_cache(path: str) -> bytes | None:
    """Return cached image bytes or None when stale/missing."""
    try:
        if time.time() - os.path.getmtime(path) > _IMAGE_CACHE_MAX_AGE:
            os.unlink(path)
            return None
        with open(path, "rb") as fh:
            return fh.read()
    except (FileNotFoundError, PermissionError, OSError):
        return None


def _write_cache(path: str, data: bytes) -> None:
    """Write to disk cache, silently ignoring errors."""
    try:
        with open(path, "wb") as fh:
            fh.write(data)
    except OSError:
        pass


def _fetch_and_maybe_resize(
    url: str,
    width: int | None,
    max_bytes: int,
) -> bytes:
    """Fetch one CivitAI image, optionally resize, cache, return JPEG.

    When ``width`` is provided the image is resized server-side to
    keep response sizes small (typically 10-50KB for thumbnails).
    Failed/fetches are NOT cached so they will be retried next time.
    """
    cache_path = _image_cache_path(url, width)
    cached = _image_from_cache(cache_path)
    if cached is not None:
        return cached

    # Rate-limit to avoid CivitAI rejecting requests
    _rate_limit_image_fetch()

    raw = safe_fetch_bytes(url, max_bytes=max_bytes)

    if width is not None:
        try:
            img = PILImage.open(io.BytesIO(raw)).convert("RGB")
            ratio = width / float(img.width)
            h = int(float(img.height) * ratio)
            img = img.resize((width, h), PILImage.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85, optimize=True)
            resized = buf.getvalue()
            # Only cache on successful resize
            _write_cache(cache_path, resized)
            return resized
        except Exception:
            # Resize failed — return raw bytes but don't cache
            return raw

    # No resize requested — cache the original
    _write_cache(cache_path, raw)
    return raw


@router.post("/civitai/image")
async def fetch_civitai_image_route(
    payload: CivitaiImageRequest,
) -> Response:
    """Return one CivitAI preview image through the daemon process.

    The image is cached on disk by URL+width for 24 hours.
    When ``width`` is provided the image is resized server-side
    with Pillow, keeping response payloads small regardless of
    the original CivitAI resolution.
    """
    try:
        image_bytes = await asyncio.to_thread(
            _fetch_and_maybe_resize,
            payload.url,
            payload.width,
            payload.max_bytes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return Response(
        content=image_bytes,
        media_type="image/jpeg",
    )


@router.get("/status/{job_id}/stream")
async def stream_download_progress(
    job_id: str,
    request: Request,
) -> StreamingResponse:
    """SSE stream that emits download progress events for one job.

    Events:
      ``{"type": "progress", "progress": 42.5, "status": "running", ...}``
      ``{"type": "complete", "result": {...}}``
      ``{"type": "error", "error": "message"}``
      ``{"type": "cancelled"}``
    """
    service = get_download_job_service(request)

    async def event_stream():
        try:
            while True:
                if await request.is_disconnected():
                    break
                job = await service.get_status(job_id)
                if job is None:
                    yield (
                        b"data: "
                        + json.dumps(
                            {"type": "error", "error": "Job not found"},
                        ).encode("utf-8")
                        + b"\n\n"
                    )
                    break
                status = job.status.value
                payload = {
                    "type": "progress",
                    "progress": job.progress,
                    "status": status,
                    "metadata": job.metadata,
                }
                yield (
                    b"data: "
                    + json.dumps(payload).encode("utf-8")
                    + b"\n\n"
                )
                if status in ("completed", "failed", "cancelled"):
                    if status == "completed":
                        yield (
                            b"data: "
                            + json.dumps(
                                {
                                    "type": "complete",
                                    "result": job.result,
                                },
                            ).encode("utf-8")
                            + b"\n\n"
                        )
                    elif status == "failed":
                        yield (
                            b"data: "
                            + json.dumps(
                                {"type": "error", "error": job.error},
                            ).encode("utf-8")
                            + b"\n\n"
                        )
                    else:
                        yield (
                            b"data: "
                            + json.dumps({"type": "cancelled"}).encode(
                                "utf-8",
                            )
                            + b"\n\n"
                        )
                    break
                await asyncio.sleep(0.25)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/status/{job_id}",
    response_model=DownloadJobStatusResponse,
)
async def get_download_job_status(
    job_id: str,
    request: Request,
) -> DownloadJobStatusResponse:
    """Return the tracked state for one download job."""
    service = get_download_job_service(request)
    job = await service.get_status(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Download job not found")
    return DownloadJobStatusResponse(**job.to_dict())


@router.delete(
    "/cancel/{job_id}",
    response_model=DownloadJobAcceptedResponse,
)
async def cancel_download_job(
    job_id: str,
    request: Request,
) -> DownloadJobAcceptedResponse:
    """Cancel one running download job when possible."""
    service = get_download_job_service(request)
    job = await service.get_status(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Download job not found")
    await service.cancel(job_id)
    updated_job = await service.get_status(job_id)
    status = "cancelled"
    if updated_job is not None:
        status = updated_job.status.value
    return DownloadJobAcceptedResponse(job_id=job_id, status=status)

