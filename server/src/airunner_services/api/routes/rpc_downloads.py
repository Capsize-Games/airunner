"""RPC handlers: downloads (HuggingFace + CivitAI)."""

from __future__ import annotations

import asyncio
from typing import Any

from airunner_services.api.routes.events import _rpc_register
from airunner_services.api.routes.events_bus import WsEventBus
from airunner_services.api.routes.events_rpc import EVENT_CIVITAI_THUMBNAIL
from airunner_services.downloads.civitai_filters import (
    _BASE_MODEL_ALIASES,
    _MODEL_TYPE_ALIASES,
)
from airunner_services.downloads.civitai_thumbnails import _fetch_cached_image
from airunner_services.downloads.job_service import DownloadJobService
from airunner_services.downloads.service import (
    fetch_civitai_browser_model_info as fetch_browser_fn,
    fetch_civitai_model_info as fetch_info_fn,
    search_civitai_models as search_fn,
)


@_rpc_register("POST", "/api/v1/downloads/huggingface")
async def _rpc_downloads_hf(body: dict, **kw: Any) -> dict[str, Any]:
    """Start a HuggingFace download."""
    try:
        service = DownloadJobService()
        job_id = await asyncio.to_thread(
            service.start_huggingface_download,
            repo_id=str(body.get("repo_id", "")),
            model_type=str(body.get("model_type", "llm")),
            output_dir=body.get("output_dir"),
            missing_files=body.get("missing_files"),
            gguf_filename=body.get("gguf_filename"),
            prefer_pre_quantized=body.get("prefer_pre_quantized"),
        )
        return {"status": 200, "body": {"job_id": job_id}}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("GET", "/api/v1/downloads/status/{job_id}")
async def _rpc_downloads_status(body: dict, **kw: Any) -> dict[str, Any]:
    """Get download job status."""
    pp: dict = kw.get("path_params", {})
    job_id = pp.get("job_id", "")
    try:
        service = DownloadJobService()
        state = await asyncio.to_thread(service.get_status, job_id)
        if state is None:
            return {"status": 404, "body": {"error": "Job not found"}}
        return {
            "status": 200,
            "body": {
                "job_id": state.job_id,
                "status": state.status,
                "progress": state.progress,
                "result": state.result,
                "error": state.error,
                "metadata": state.metadata,
            },
        }
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("DELETE", "/api/v1/downloads/cancel/{job_id}")
async def _rpc_downloads_cancel(body: dict, **kw: Any) -> dict[str, Any]:
    """Cancel a download job."""
    pp: dict = kw.get("path_params", {})
    job_id = pp.get("job_id", "")
    try:
        service = DownloadJobService()
        cancelled = await asyncio.to_thread(service.cancel, job_id)
        if not cancelled:
            return {"status": 404, "body": {"error": "Job not found"}}
        return {
            "status": 200,
            "body": {"job_id": job_id, "status": "cancelled"},
        }
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("POST", "/api/v1/downloads/civitai/models")
async def _rpc_downloads_civitai_search(
    body: dict, **kw: Any
) -> dict[str, Any]:
    """Search CivitAI models."""
    try:
        result = await asyncio.to_thread(
            search_fn,
            str(body.get("query", "")),
            base_models=body.get("base_models"),
            model_types=body.get("model_types"),
            limit=int(body.get("limit", 20)),
            cursor=body.get("cursor"),
            api_key=str(body.get("api_key", "")),
        )
        # Fire background task to stream thumbnails via event bus
        items = (result.get("items") or []) if isinstance(result, dict) else []
        if items:
            import logging
            logging.getLogger(
                "airunner_services.api.routes.rpc_downloads",
            ).info(
                "SEARCH returned %d items, starting stream", len(items),
            )
            asyncio.create_task(_stream_civitai_thumbnails(items))
        return {"status": 200, "body": result}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("POST", "/api/v1/downloads/civitai/model")
async def _rpc_downloads_civitai_model(
    body: dict, **kw: Any
) -> dict[str, Any]:
    """Get CivitAI model detail."""
    try:
        result = await asyncio.to_thread(
            fetch_browser_fn,
            str(body.get("model_id", "")),
            base_models=body.get("base_models"),
            model_types=body.get("model_types"),
            api_key=str(body.get("api_key", "")),
        )
        # Fire background task to stream version thumbnails
        if isinstance(result, dict):
            asyncio.create_task(_stream_version_thumbnails_bg(result))
        return {"status": 200, "body": result}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("POST", "/api/v1/downloads/civitai/file")
async def _rpc_downloads_civitai_file(body: dict, **kw: Any) -> dict[str, Any]:
    """Start a CivitAI file download."""
    try:
        service = DownloadJobService()
        job_id = await asyncio.to_thread(
            service.start_civitai_file_download,
            str(body.get("url", "")),
            output_path=str(body.get("output_path", "")),
            file_size=int(body.get("file_size", 0)),
            api_key=str(body.get("api_key", "")),
        )
        return {"status": 200, "body": {"job_id": job_id}}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("POST", "/api/v1/downloads/civitai/info")
async def _rpc_downloads_civitai_info(body: dict, **kw: Any) -> dict[str, Any]:
    """Get CivitAI model info by URL."""
    try:
        result = await asyncio.to_thread(
            fetch_info_fn,
            str(body.get("url", "")),
            str(body.get("api_key", "")),
        )
        return {"status": 200, "body": result}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


def _stream_one_thumbnail(item: dict) -> None:
    """Fetch and broadcast a thumbnail for one search result."""
    import logging
    dl_logger = logging.getLogger("airunner_services.api.routes.rpc_downloads")
    from airunner_services.downloads.civitai_thumbnails import (
        _fetch_thumbnail_b64,
        _first_image_url,
    )
    bus = WsEventBus()
    versions = item.get("modelVersions") or []
    if not versions:
        return
    url = _first_image_url(versions[0].get("images") or [])
    if not url:
        return
    model_id = item.get("id")
    try:
        b64 = _fetch_thumbnail_b64(url)
    except Exception as exc:
        dl_logger.warning(
            "STREAM model=%s FAILED: %s", model_id, exc,
        )
        return
    dl_logger.info("STREAM model=%s OK", model_id)
    bus.broadcast(
        EVENT_CIVITAI_THUMBNAIL,
        {"model_id": model_id, "thumbnails": {"small": b64}},
    )


@_rpc_register("POST", "/api/v1/downloads/civitai/version-thumbnails")
async def _rpc_downloads_civitai_version_thumbs(
    body: dict, **kw: Any
) -> dict[str, Any]:
    """Start background thumbnail embedding for one version of a model."""
    model_data = body.get("model_data")
    version_index = int(body.get("version_index", 0))
    if not model_data:
        return {"status": 400, "body": {"error": "Missing model_data"}}
    asyncio.create_task(_stream_one_version_bg(model_data, version_index))
    return {"status": 200, "body": {"status": "started"}}


def _stream_one_version_sync(model_data: dict, version_index: int) -> None:
    """Embed thumbnails on one version's images, broadcasting each as it completes."""
    from airunner_services.downloads.civitai_thumbnails import (
        embed_single_version_streaming,
    )
    model_id = model_data.get("id")
    bus = WsEventBus()

    def _on_image_done(img: dict) -> None:
        url = str(img.get("url") or img.get("thumbnailUrl") or "")
        b64 = img.get("images_base64") or {}
        if url and b64:
            bus.broadcast(
                EVENT_CIVITAI_THUMBNAIL,
                {
                    "model_id": model_id,
                    "version_index": version_index,
                    "image_url": url,
                    "images_base64": b64,
                },
            )

    embed_single_version_streaming(model_data, version_index, _on_image_done)


async def _stream_one_version_bg(
    model_data: dict, version_index: int,
) -> None:
    await asyncio.to_thread(_stream_one_version_sync, model_data, version_index)


def _stream_thumbnails_sync(items: list) -> None:
    """Synchronous thumbnail streaming with concurrent fetches."""
    import concurrent.futures
    import logging
    dl_logger = logging.getLogger("airunner_services.api.routes.rpc_downloads")
    total = len(items)
    dl_logger.info("STREAM starting: %d items (concurrent)", total)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(_stream_one_thumbnail, items))
    dl_logger.info("STREAM finished: %d items", total)


def _stream_version_thumbnails_sync(model_data: dict) -> None:
    """Embed thumbnails for the initial version (index 0), broadcasting each image as it completes."""
    _stream_one_version_sync(model_data, 0)


async def _stream_version_thumbnails_bg(model_data: dict) -> None:
    await asyncio.to_thread(_stream_version_thumbnails_sync, model_data)


async def _stream_civitai_thumbnails(items: list) -> None:
    """Run thumbnail streaming in a thread to avoid blocking the event loop."""
    await asyncio.to_thread(_stream_thumbnails_sync, items)


@_rpc_register("GET", "/api/v1/downloads/civitai/options")
async def _rpc_downloads_civitai_options(
    body: dict, **kw: Any
) -> dict[str, Any]:
    """Get CivitAI filter options."""
    try:
        base_models = [
            {"label": label, "value": value}
            for label, value in _BASE_MODEL_ALIASES.items()
        ]
        model_types = sorted(set(_MODEL_TYPE_ALIASES.values()))
        return {
            "status": 200,
            "body": {
                "base_models": base_models,
                "model_types": model_types,
            },
        }
    except Exception:
        return {"status": 200, "body": {"base_models": [], "model_types": []}}


@_rpc_register("POST", "/api/v1/downloads/civitai/image")
async def _rpc_downloads_civitai_image(
    body: dict, **kw: Any
) -> dict[str, Any]:
    """Fetch, cache, and return a CivitAI image through the server proxy."""
    url = str(body.get("url", ""))
    width = int(body.get("width", 0))
    if width <= 0 or width > 1200:
        width = 500
    if not url:
        return {"status": 400, "body": {"error": "Missing url"}}
    try:
        img_data, content_type = _fetch_cached_image(url, width)
        return {
            "status": 200,
            "body": img_data,
            "headers": {"content-type": content_type},
            "binary": True,
        }
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}
