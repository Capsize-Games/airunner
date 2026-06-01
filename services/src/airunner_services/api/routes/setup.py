"""Setup installation endpoint — moves model download orchestration
from the GUI setup wizard into the daemon.

The daemon receives a declarative install configuration and runs all
directory creation, model downloads, NLTK/unidic data installation
server-side.  Progress is streamed via SSE.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import nltk
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from airunner_services.bootstrap.model_bootstrap_data import (
    model_bootstrap_data,
)
from airunner_services.settings import AIRUNNER_BASE_PATH

router = APIRouter()
logger = logging.getLogger(__name__)


class SetupInstallRequest(BaseModel):
    """Declarative setup install configuration."""

    enabled_models: dict[str, bool] = {}
    base_path: str = str(AIRUNNER_BASE_PATH)
    prefer_pre_quantized: bool = True


def _emit(msg: dict[str, Any]) -> str:
    """Return one SSE-formatted event string."""
    return f"data: {json.dumps(msg)}\n\n"


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


async def _install_nltk_data() -> list[str]:
    """Install required NLTK data packages."""
    packages = [
        "punkt",
        "punkt_tab",
        "averaged_perceptron_tagger",
        "averaged_perceptron_tagger_eng",
    ]
    installed = []
    for pkg in packages:
        try:
            nltk.download(pkg, quiet=True)
            installed.append(pkg)
        except Exception as exc:
            logger.warning("NLTK download failed for %s: %s", pkg, exc)
    return installed


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
            if model.get("category") not in {None, "art"}:
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
    """Install AIRunner models and data through the daemon."""

    async def _stream():
        download_service = getattr(
            request.app.state, "download_job_service", None,
        )

        # Phase 1: Create directories
        yield _emit({"status": "installing", "message": "Creating directories...", "progress": 0})
        created = _create_directories(payload.base_path)
        yield _emit({"status": "installing", "message": f"Created {len(created)} directories", "progress": 2})

        # Phase 2: Install NLTK data
        yield _emit({"status": "installing", "message": "Installing NLTK data...", "progress": 5})
        nltk_installed = await _install_nltk_data()
        yield _emit({"status": "installing", "message": f"NLTK installed: {nltk_installed}", "progress": 8})

        # Phase 3: Queue downloads
        jobs = _resolve_download_jobs(payload.enabled_models)
        total_jobs = len(jobs)
        yield _emit({"status": "installing", "message": f"Queuing {total_jobs} model downloads...", "progress": 10})

        if download_service is None:
            yield _emit({"status": "completed", "message": "Setup complete (no download service available)", "progress": 100})
            return

        for idx, job in enumerate(jobs):
            try:
                job_id = await download_service.start_huggingface_download(
                    repo_id=job["repo_id"],
                    model_type=job["model_type"],
                    prefer_pre_quantized=payload.prefer_pre_quantized,
                )
                yield _emit({
                    "status": "installing",
                    "message": f"Started: {job['repo_id']}",
                    "progress": 10 + int(85 * idx / max(total_jobs, 1)),
                    "job_id": job_id,
                    "repo_id": job["repo_id"],
                })
            except Exception as exc:
                logger.warning("Failed to queue %s: %s", job["repo_id"], exc)
                yield _emit({
                    "status": "installing",
                    "message": f"Failed: {job['repo_id']} — {exc}",
                    "progress": 10 + int(85 * idx / max(total_jobs, 1)),
                })

        yield _emit({"status": "completed", "message": "Setup complete", "progress": 100})

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
