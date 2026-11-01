"""Administrative setup installation and model download orchestration.

The daemon receives a declarative install configuration and runs all
directory creation, model downloads, NLTK/unidic data installation
server-side.  Progress is streamed via SSE.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic import field_validator

from airunner_services.api.admin_auth import require_admin_key
from airunner_services.url_safety import is_offline_mode

from airunner_services.bootstrap.model_bootstrap_data import (
    model_bootstrap_data,
)
from airunner_common.settings import AIRUNNER_BASE_PATH
from .setup_nltk import install_nltk_data as _install_nltk_data

router = APIRouter()
logger = logging.getLogger(__name__)


class SetupInstallRequest(BaseModel):
    """Declarative setup install configuration."""

    enabled_models: dict[str, bool] = {}
    base_path: str = str(AIRUNNER_BASE_PATH)
    prefer_pre_quantized: bool = True

    @field_validator("enabled_models")
    @classmethod
    def supported_models(cls, value: dict[str, bool]) -> dict[str, bool]:
        """Reject configuration keys the installer cannot implement."""
        if set(value) - {"llm", "stable_diffusion"}:
            raise ValueError("Unsupported setup model family")
        return value


def _emit(msg: dict[str, Any]) -> str:
    """Return one SSE-formatted event string."""
    return f"data: {json.dumps(msg)}\n\n"


def _allowed_base_roots() -> list[str]:
    """Return the real paths a setup install may create directories in."""
    return [
        os.path.realpath(os.path.expanduser(str(AIRUNNER_BASE_PATH)))
    ]


def _resolve_base_path(raw: str) -> str:
    """Resolve an install base path confined to the allowed data root.

    Symlinks, ``..`` segments, and tilde are resolved before the
    comparison, so a value that escapes the data root is rejected
    instead of letting an authenticated caller create directories
    anywhere the daemon can write.
    """
    candidate = os.path.realpath(os.path.expanduser(raw or ""))
    for root in _allowed_base_roots():
        if candidate == root or candidate.startswith(root + os.sep):
            return candidate
    raise HTTPException(
        status_code=400, detail="base_path_outside_allowed_root"
    )


def _create_directories(base_path: str) -> list[str]:
    """Create AIRunner data directories and return created paths."""
    dirs = [
        "art/models",
        "text/models/llm/causallm",
        "text/models/stt",
        "text/models/tts",
        "text/models/tts/openvoice",
        "documents",
        "ebooks",
        "images",
        "rag_index",
        "webpages",
        "map",
    ]
    created = []
    for subdir in dirs:
        path = os.path.expanduser(os.path.join(base_path, subdir))
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            created.append(path)
    return created


def _resolve_download_jobs(
    enabled: dict[str, bool],
) -> list[dict[str, Any]]:
    """Return a list of download job payloads from the install config."""
    jobs: list[dict[str, Any]] = []

    if enabled.get("llm"):
        for model in model_bootstrap_data:
            if model.get("category") != "llm":
                continue
            jobs.append({
                "repo_id": model["path"],
                "model_type": "llm",
                "category": model.get("category", ""),
            })

    if enabled.get("stable_diffusion"):
        for model in model_bootstrap_data:
            if model.get("model_type") != "art":
                continue
            if model.get("pipeline_action") == "embedding":
                continue
            jobs.append({
                "repo_id": model["path"],
                "model_type": "art",
                "version": model.get("version", ""),
                "pipeline_action": model.get("pipeline_action", ""),
            })

    return jobs


@router.post("/install")
async def setup_install(
    payload: SetupInstallRequest,
    request: Request,
):
    """Install data and queue model downloads with explicit outcomes."""
    require_admin_key(request)
    resolved_base = _resolve_base_path(payload.base_path)
    if is_offline_mode():
        raise HTTPException(403, "offline_mode")
    jobs = _resolve_download_jobs(payload.enabled_models)
    if len(jobs) > 16:
        raise HTTPException(400, "too_many_setup_downloads")
    download_service = getattr(request.app.state, "download_job_service", None)
    if jobs and download_service is None:
        raise HTTPException(503, "download_service_unavailable")

    async def _stream():
        # Phase 1: Create directories
        yield _emit({"status": "installing", "message": "Creating directories...", "progress": 0})
        try:
            created = _create_directories(resolved_base)
        except OSError:
            logger.exception("Setup directory creation failed")
            yield _emit({"status": "failed", "message": "Directory creation failed"})
            return
        yield _emit({"status": "installing", "message": f"Created {len(created)} directories", "progress": 2})

        # Phase 2: Install NLTK data
        yield _emit({"status": "installing", "message": "Installing NLTK data...", "progress": 5})
        try:
            nltk_installed = await _install_nltk_data(resolved_base)
        except Exception:
            logger.exception("Setup data installation failed")
            yield _emit({"status": "failed", "message": "Data installation failed"})
            return
        yield _emit({"status": "installing", "message": f"NLTK installed: {nltk_installed}", "progress": 8})

        # Phase 3: Queue downloads
        total_jobs = len(jobs)
        yield _emit({"status": "installing", "message": f"Queuing {total_jobs} model downloads...", "progress": 10})

        queued = 0
        for idx, job in enumerate(jobs):
            try:
                job_id = await download_service.start_huggingface_download(
                    repo_id=job["repo_id"],
                    model_type=job["model_type"],
                    prefer_pre_quantized=payload.prefer_pre_quantized,
                )
                if not job_id:
                    raise RuntimeError("Download was not queued")
                queued += 1
                yield _emit({
                    "status": "queued",
                    "message": f"Started: {job['repo_id']}",
                    "progress": 10 + int(85 * idx / max(total_jobs, 1)),
                    "job_id": job_id,
                    "repo_id": job["repo_id"],
                })
            except Exception as exc:
                logger.warning("Failed to queue %s: %s", job["repo_id"], exc)
                # Generic message only; the exception detail stays in the
                # server log (CodeQL py/stack-trace-exposure, issue #2079).
                yield _emit({
                    "status": "failed",
                    "message": f"Failed: {job['repo_id']}",
                    "progress": 10 + int(85 * idx / max(total_jobs, 1)),
                })

        if queued < total_jobs:
            status = "partial" if queued else "failed"
            message = "Some downloads were not queued"
        elif total_jobs:
            status, message = "queued", "Model downloads queued"
        else:
            status, message = "completed", "Data installation complete"
        yield _emit({
            "status": status, "message": message, "progress": 100,
            "queued": queued, "failed": total_jobs - queued,
        })

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
