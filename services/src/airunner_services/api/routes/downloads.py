"""Download job endpoints for service-owned model acquisition."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import logging
import os
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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


# ── HuggingFace endpoints ──


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


# ── URL endpoints ──


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


# ── NLTK endpoints ──


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


# ── CivitAI common endpoints ──


def _thumbnail_url(item: dict[str, Any]) -> str | None:
    """Extract the first usable thumbnail URL from a CivitAI search item."""
    versions = item.get("modelVersions", [])
    if versions:
        images = versions[0].get("images", [])
        if images:
            url = str(images[0].get("url") or images[0].get("thumbnailUrl") or "")
            if url:
                logger.debug("_thumbnail_url: model=%s url_hash=%s", item.get("id"), hashlib.sha256(url.encode()).hexdigest()[:12])
            else:
                logger.debug("_thumbnail_url: model=%s has image but no usable url", item.get("id"))
            return url if url else None
        else:
            logger.debug("_thumbnail_url: model=%s has version but no images", item.get("id"))
    else:
        logger.debug("_thumbnail_url: model=%s has no versions", item.get("id"))
    return None


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


# ── CivitAI search cache (72h TTL, server-side, file-backed) ──

_SEARCH_CACHE_DIR = os.path.join(
    "/tmp", "airunner", "civitai_search_cache",
)
_SEARCH_CACHE_TTL = 72 * 3600  # 72 hours


def _search_cache_key(
    query: str,
    base_models: list[str] | None,
    model_types: list[str] | None,
    cursor: str | None,
) -> str:
    raw = json.dumps(
        [query, base_models, model_types, cursor], sort_keys=True,
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _search_cache_get(key: str) -> dict[str, Any] | None:
    path = os.path.join(_SEARCH_CACHE_DIR, f"{key}.json")
    try:
        if time.time() - os.path.getmtime(path) > _SEARCH_CACHE_TTL:
            os.unlink(path)
            return None
        with open(path, "r") as fh:
            return json.load(fh)
    except OSError:
        return None


def _search_cache_set(key: str, data: dict[str, Any]) -> None:
    os.makedirs(_SEARCH_CACHE_DIR, exist_ok=True)
    path = os.path.join(_SEARCH_CACHE_DIR, f"{key}.json")
    try:
        with open(path, "w") as fh:
            json.dump(data, fh)
    except OSError:
        pass


# ── CivitAI image cache (permanent, sized) ──

_IMAGE_CACHE_DIR = os.path.join(
    "/tmp", "airunner", "civitai_image_cache",
)
_IMAGE_MAX_PX = 500  # longest side


def _image_cache_path(url: str, suffix: str) -> str:
    """Return cache path for one named size of one image."""
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    subdir = os.path.join(_IMAGE_CACHE_DIR, suffix)
    os.makedirs(subdir, exist_ok=True)
    return os.path.join(subdir, f"{digest}.jpg")


def _image_from_cache(path: str) -> bytes | None:
    """Return cached image bytes or None when missing (permanent cache)."""
    try:
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


def _resize_image(raw: bytes, target_px: int) -> bytes:
    """Resize one image so the longest side is ``target_px``, return JPEG."""
    try:
        img = PILImage.open(io.BytesIO(raw)).convert("RGB")
        ratio = target_px / max(img.width, img.height)
        if ratio >= 1.0 and target_px >= _IMAGE_MAX_PX:
            # Full-size: cap at _IMAGE_MAX_PX but never upscale
            ratio = min(1.0, _IMAGE_MAX_PX / max(img.width, img.height))
        new_w = max(1, int(img.width * ratio))
        new_h = max(1, int(img.height * ratio))
        img = img.resize((new_w, new_h), PILImage.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        return buf.getvalue()
    except Exception:
        return raw


def _fetch_and_prepare_sizes(url: str) -> dict[str, bytes]:
    """Fetch one image, prepare & cache three sizes, return them.

    Sizes:
      - ``small``: 40px  (search list thumbnails)
      - ``medium``: 200px (modal preview grid)
      - ``full``:   500px max (detail view)
    """
    sizes = {"small": 40, "medium": 200, "full": _IMAGE_MAX_PX}
    result: dict[str, bytes] = {}

    # Check cache for all sizes
    for name in sizes:
        path = _image_cache_path(url, name)
        cached = _image_from_cache(path)
        if cached is not None:
            result[name] = cached

    if len(result) == len(sizes):
        return result

    # Fetch once, use for all sizes
    raw = safe_fetch_bytes(url, max_bytes=50_000_000)
    for name, px in sizes.items():
        path = _image_cache_path(url, name)
        if name in result:
            continue
        data = _resize_image(raw, px)
        _write_cache(path, data)
        result[name] = data

    return result


# ── CivitAI search with inline thumbnails ──


_THUMBNAIL_WORKERS = 6  # parallel CivitAI image fetches


def _attach_thumbnails(
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach ``thumbnails`` (base64) to each search item.

    Only the ``small`` (40px) size is included to keep responses fast
    and compact.  Larger sizes (medium/full) are embedded in the model
    detail endpoint.
    """
    # Collect all fetchable URLs first
    url_map: list[tuple[int, int, str]] = []  # (list_idx, model_id, url)
    for idx, item in enumerate(items):
        model_id = int(item.get("id", 0))
        thumb_url = _thumbnail_url(item)
        if thumb_url:
            url_map.append((idx, model_id, thumb_url))
        else:
            logger.debug("_attach_thumbnails: NO URL model=%s", model_id)

    if not url_map:
        logger.info("_attach_thumbnails: done total=%d ok=0 no_url=%d", len(items), len(items))
        return [{**item, "thumbnails": {}} for item in items]

    # Fetch in parallel — only embed the "small" (40px) size
    results: dict[int, dict[str, str]] = {}
    with ThreadPoolExecutor(max_workers=_THUMBNAIL_WORKERS) as pool:
        fut_map = {
            pool.submit(_fetch_and_prepare_sizes, url): (list_idx, model_id)
            for list_idx, model_id, url in url_map
        }
        for fut in as_completed(fut_map):
            list_idx, model_id = fut_map[fut]
            try:
                sizes = fut.result()
                thumb_data: dict[str, str] = {}
                blob = sizes.get("small")
                if blob:
                    thumb_data["small"] = base64.b64encode(blob).decode()
                results[list_idx] = thumb_data
                logger.debug("_attach_thumbnails: OK model=%s small=%d", model_id, len(blob) if blob else 0)
            except Exception as exc:
                logger.warning("_attach_thumbnails: FAIL model=%s error=%s", model_id, type(exc).__name__)
                results[list_idx] = {}

    # Build output preserving order
    out = []
    for idx, item in enumerate(items):
        out.append({**item, "thumbnails": results.get(idx, {})})

    ok_count = sum(1 for r in results.values() if r)
    logger.info(
        "_attach_thumbnails: done total=%d ok=%d fail=%d no_url=%d",
        len(items), ok_count, len(url_map) - ok_count,
        len(items) - len(url_map),
    )
    return out


@router.post("/civitai/models")
async def search_civitai_models_route(
    payload: CivitaiBrowserSearchRequest,
) -> dict[str, Any]:
    """Return filtered CivitAI search results with inline 40px thumbnails.

    Search results are cached server-side for 72 hours.
    Images are cached permanently once fetched.
    """
    # Check server-side cache (72h) for search metadata
    cache_key = _search_cache_key(
        payload.query,
        payload.base_models,
        payload.model_types,
        payload.cursor,
    )
    cached = _search_cache_get(cache_key)
    if cached is not None:
        logger.debug("CivitAI search cache HIT")
        # Attach thumbnails (may hit image cache)
        cached["items"] = _attach_thumbnails(cached.get("items", []))
        return cached

    logger.info(
        "CivitAI search: query=%r base_models=%s model_types=%s "
        "limit=%s cursor=%s",
        payload.query,
        payload.base_models,
        payload.model_types,
        payload.limit,
        "set" if payload.cursor else None,
    )
    try:
        result = await asyncio.to_thread(
            search_civitai_models,
            payload.query,
            base_models=payload.base_models,
            model_types=payload.model_types,
            limit=payload.limit,
            cursor=payload.cursor,
            api_key=payload.api_key or "",
        )
        item_count = len(result.get("items", []))
        next_cursor = (
            result.get("metadata", {}).get("nextCursor")
            if isinstance(result.get("metadata"), dict)
            else None
        )
        logger.info(
            "CivitAI search OK: %d items, nextCursor=%s",
            item_count, "set" if next_cursor else None,
        )

        # Cache the search metadata (without thumbnails to save space)
        cache_item = {
            "items": result.get("items", []),
            "metadata": result.get("metadata"),
        }
        _search_cache_set(cache_key, cache_item)

        # Attach thumbnails (may hit image cache)
        result["items"] = _attach_thumbnails(result.get("items", []))
        total_b64 = sum(
            len(v) for item in result.get("items", [])
            for v in (item.get("thumbnails", {}) or {}).values()
        )
        logger.info(
            "CivitAI search response: %d items, %d bytes of base64 thumbnails",
            len(result.get("items", [])), total_b64,
        )
        return result
    except Exception:
        logger.exception("CivitAI search failed")
        raise


# ── CivitAI model detail with inline images ──


def _embed_version_images(
    versions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach ``images_base64`` to images for each version.

    Only the **first version** gets full image embeds (small/medium/full).
    Remaining versions return metadata only — the client lazily fetches
    them when the user switches versions.

    Fetches the first version's images in parallel.
    """
    if not versions:
        return versions

    # Only embed images for the first version
    first_version = versions[0]
    first_images = first_version.get("images", [])
    url_map: list[tuple[int, str]] = []  # (img_idx, url)
    for ii, img in enumerate(first_images):
        url = str(img.get("url") or img.get("thumbnailUrl") or "")
        if url:
            url_map.append((ii, url))

    fetched: dict[int, dict[str, bytes]] = {}
    if url_map:
        with ThreadPoolExecutor(max_workers=_THUMBNAIL_WORKERS) as pool:
            fut_map = {
                pool.submit(_fetch_and_prepare_sizes, url): ii
                for ii, url in url_map
            }
            for fut in as_completed(fut_map):
                ii = fut_map[fut]
                try:
                    fetched[ii] = fut.result()
                except Exception:
                    fetched[ii] = {}

    # Build first version with embedded images
    embedded_first: list[dict[str, Any]] = []
    for ii, img in enumerate(first_images):
        url = str(img.get("url") or img.get("thumbnailUrl") or "")
        sizes = fetched.get(ii, {})
        imgs_b64: dict[str, str] = {}
        for name, blob in sizes.items():
            imgs_b64[name] = base64.b64encode(blob).decode()
        embedded_first.append({
            "url": url,
            "nsfw": img.get("nsfw"),
            "width": img.get("width"),
            "height": img.get("height"),
            "images_base64": imgs_b64,
        })

    out = [{**first_version, "images": embedded_first}]
    # Remaining versions: metadata only, no base64
    for version in versions[1:]:
        out.append(version)

    logger.info(
        "_embed_version_images: %d versions, first version has %d images with base64",
        len(versions), len(url_map),
    )
    return out


@router.post("/civitai/model")
async def fetch_civitai_browser_model_route(
    payload: CivitaiBrowserModelRequest,
) -> dict[str, Any]:
    """Return one filtered model detail with all images embedded as base64."""
    logger.info(
        "CivitAI model detail request: model_id=%s", payload.model_id,
    )
    try:
        raw = await asyncio.to_thread(
            fetch_civitai_browser_model_info,
            payload.model_id,
            base_models=payload.base_models,
            model_types=payload.model_types,
            api_key=payload.api_key or "",
        )
        raw["modelVersions"] = _embed_version_images(
            raw.get("modelVersions", []),
        )
        total_b64 = sum(
            len(v) for version in raw.get("modelVersions", [])
            for img in version.get("images", [])
            for v in (img.get("images_base64", {}) or {}).values()
        )
        logger.info(
            "CivitAI model detail OK: model_id=%s %d versions, "
            "%d bytes base64 images",
            payload.model_id, len(raw.get("modelVersions", [])), total_b64,
        )
        return raw
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Legacy single-image endpoint (fallback) ──


@router.post("/civitai/image")
async def fetch_civitai_image_route(
    payload: CivitaiImageRequest,
) -> Response:
    """Return one CivitAI preview image (sized, cached permanently).

    The server fetches, resizes to 500px max, caches permanently,
    and returns JPEG bytes.  This endpoint is a fallback — prefer
    the inline base64 thumbnails from the search/detail endpoints.
    """
    try:
        sizes = await asyncio.to_thread(
            _fetch_and_prepare_sizes,
            payload.url,
        )
        # Map width hint to named size
        if payload.width and payload.width <= 60:
            key = "small"
        elif payload.width and payload.width <= 300:
            key = "medium"
        else:
            key = "full"
        image_bytes = sizes.get(key, sizes.get("full", b""))
        if not image_bytes:
            raise HTTPException(status_code=502, detail="Image fetch failed")
        return Response(content=image_bytes, media_type="image/jpeg")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Legacy endpoints (kept for backward compat) ──


@router.get("/civitai/images/ready")
async def watch_image_ready():
    """SSE stream (legacy - no longer required with inline thumbnails)."""
    async def empty_stream():
        yield b": legacy endpoint - no retry needed\n\n"
    return StreamingResponse(
        empty_stream(),
        media_type="text/event-stream",
    )
