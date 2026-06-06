"""RPC handlers: downloads (HuggingFace + CivitAI)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from airunner_services.api.routes.events import _rpc_register
from airunner_services.api.routes.rpc_downloads_helpers import (
    _stream_civitai_thumbnails,
    _stream_one_version_bg,
    _stream_version_thumbnails_bg,
    _thumbnail_cancel_events,
    _thumbnail_cancel_lock,
)
from airunner_services.downloads.civitai_filters import (
    _BASE_MODEL_ALIASES,
    _MODEL_TYPE_ALIASES,
    _MODEL_TYPES_BY_BASE,
)
from airunner_services.downloads.civitai_thumbnails import _fetch_cached_image
from airunner_services.downloads.job_service import DownloadJobService
from airunner_services.downloads.service import (
    fetch_civitai_browser_model_info as fetch_browser_fn,
    fetch_civitai_model_info as fetch_info_fn,
    search_civitai_models as search_fn,
)

_log = logging.getLogger(__name__)

_EMPTY_OPTIONS: dict[str, Any] = {
    "base_models": [],
    "model_types": [],
    "model_types_by_base": {},
}


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
        ok_body = {"job_id": job_id, "status": "cancelled"}
        return {"status": 200, "body": ok_body}
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
        items = (result.get("items") or []) if isinstance(result, dict) else []
        if items:
            _log.info("SEARCH returned %d items, starting stream", len(items))
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


@_rpc_register("POST", "/api/v1/downloads/civitai/version-thumbnails")
async def _rpc_downloads_civitai_version_thumbs(
    body: dict, **kw: Any
) -> dict[str, Any]:
    """Start background thumbnail embedding for a model version."""
    model_data = body.get("model_data")
    version_index = int(body.get("version_index", 0))
    if not model_data:
        return {"status": 400, "body": {"error": "Missing model_data"}}
    asyncio.create_task(_stream_one_version_bg(model_data, version_index))
    return {"status": 200, "body": {"status": "started"}}


@_rpc_register("DELETE", "/api/v1/downloads/civitai/version-thumbnails")
async def _rpc_downloads_civitai_cancel_thumbs(
    body: dict, **kw: Any
) -> dict[str, Any]:
    """Cancel any in-progress thumbnail streaming for a model."""
    model_id = int(body.get("model_id") or 0)
    if not model_id:
        return {"status": 400, "body": {"error": "Missing model_id"}}
    with _thumbnail_cancel_lock:
        event = _thumbnail_cancel_events.get(model_id)
        if event:
            event.set()
    resp = {"status": "cancelled", "model_id": model_id}
    return {"status": 200, "body": resp}


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
        model_types_by_base = {
            value: _MODEL_TYPES_BY_BASE.get(value, model_types)
            for value in _BASE_MODEL_ALIASES.values()
        }
        return {
            "status": 200,
            "body": {
                "base_models": base_models,
                "model_types": model_types,
                "model_types_by_base": model_types_by_base,
            },
        }
    except Exception:
        return {"status": 200, "body": _EMPTY_OPTIONS}


@_rpc_register("POST", "/api/v1/downloads/civitai/image")
async def _rpc_downloads_civitai_image(
    body: dict, **kw: Any
) -> dict[str, Any]:
    """Proxy a CivitAI image through the server cache."""
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
