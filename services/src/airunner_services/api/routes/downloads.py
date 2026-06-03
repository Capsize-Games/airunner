"""Download job endpoints for service-owned model acquisition."""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import os
import queue
import threading
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
from airunner_services.downloads.civitai import _BASE_MODEL_ALIASES, _MODEL_TYPE_ALIASES

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
    """Return available base-model and model-type filter options."""
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


# ── Image proxy with disk cache and background retry queue ──

_IMAGE_CACHE_DIR = os.path.join(
    "/tmp", "airunner", "civitai_image_cache",
)
_IMAGE_CACHE_MAX_AGE = 86400  # 24 hours

_retry_queue: queue.Queue = queue.Queue()
_retry_thread_started = False
_image_ready_subscribers: list[queue.Queue] = []
_image_ready_lock = threading.Lock()


def _image_cache_path(url: str, width: int | None) -> str:
    """Return one deterministic cache path."""
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
    except OSError:
        return None


def _write_cache(path: str, data: bytes) -> None:
    """Write to disk cache."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
    except OSError:
        pass


def _notify_image_ready(url: str) -> None:
    """Push an image-ready event to all SSE subscribers."""
    payload = (
        b"data: "
        + json.dumps(
            {"type": "image_ready", "url": url},
        ).encode("utf-8")
        + b"\n\n"
    )
    with _image_ready_lock:
        dead = []
        for q in _image_ready_subscribers:
            try:
                q.put_nowait(payload)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _image_ready_subscribers.remove(q)


def _retry_worker() -> None:
    """Background thread: retries failed CivitAI image fetches."""
    while True:
        try:
            url, width, max_bytes = _retry_queue.get(timeout=5)
        except queue.Empty:
            continue
        time.sleep(0.25)  # 4 req/s max
        try:
            cache_path = _image_cache_path(url, width)
            if _image_from_cache(cache_path) is not None:
                continue
            logger.info(
                "CivitAI image RETRY — fetching from CivitAI  width=%s",
                width,
            )
            raw = safe_fetch_bytes(url, max_bytes=max_bytes)
            if width is not None:
                try:
                    img = PILImage.open(io.BytesIO(raw)).convert("RGB")
                    ratio = width / float(img.width)
                    h = int(float(img.height) * ratio)
                    img = img.resize(
                        (width, h), PILImage.Resampling.LANCZOS,
                    )
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=85, optimize=True)
                    _write_cache(cache_path, buf.getvalue())
                except Exception:
                    _write_cache(cache_path, raw)
            else:
                _write_cache(cache_path, raw)
            _notify_image_ready(url)
        except Exception:
            # Re-queue for another retry
            _retry_queue.put((url, width, max_bytes))
            time.sleep(2.0)


def _ensure_retry_worker() -> None:
    """Start the background retry worker if not running."""
    global _retry_thread_started
    if not _retry_thread_started:
        _retry_thread_started = True
        t = threading.Thread(target=_retry_worker, daemon=True)
        t.start()


@router.get("/civitai/images/ready")
async def watch_image_ready():
    """SSE stream that emits ``{"type": "image_ready", "url": "..."}``
    when a previously-failed CivitAI image has been cached successfully
    by the background retry worker."""
    q: queue.Queue = queue.Queue(maxsize=128)
    with _image_ready_lock:
        _image_ready_subscribers.append(q)

    def _cleanup():
        with _image_ready_lock:
            if q in _image_ready_subscribers:
                _image_ready_subscribers.remove(q)

    def event_stream():
        try:
            while True:
                try:
                    yield q.get(timeout=30)
                except queue.Empty:
                    yield b": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            _cleanup()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _fetch_and_resize(
    url: str,
    width: int | None,
    max_bytes: int,
) -> bytes:
    """Fetch one CivitAI image, resize, cache, and return JPEG bytes.

    If the image is not already cached, queues a background fetch and
    raises an exception (caller returns 502). The client should retry
    after receiving an ``image_ready`` SSE event.
    """
    cache_path = _image_cache_path(url, width)
    cached = _image_from_cache(cache_path)
    if cached is not None:
        logger.debug("CivitAI cache HIT  w=%s", width)
        return cached

    logger.info("CivitAI cache MISS — queuing background fetch  w=%s", width)
    _ensure_retry_worker()
    _retry_queue.put((url, width, max_bytes))
    raise RuntimeError("Not cached — queued for background fetch")


@router.post("/civitai/image")
async def fetch_civitai_image_route(
    payload: CivitaiImageRequest,
) -> Response:
    """Return one CivitAI preview image through the daemon process.

    The image is cached on disk by URL+width for 24 hours.
    When ``width`` is provided the image is resized server-side
    with Pillow, keeping response payloads small.

    On failure (rate limit, timeout) the URL is queued for background
    retry. Subscribe to ``GET /civitai/images/ready`` for SSE
    notifications when the image becomes available, then re-request.
    """
    try:
        image_bytes = await asyncio.to_thread(
            _fetch_and_resize,
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
