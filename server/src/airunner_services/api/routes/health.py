"""Health check and status endpoints."""

import os
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from airunner_services.dev_build_token import current_dev_build_token
from airunner_services.settings import AIRUNNER_VERSION

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    uptime: float
    pid: int
    started_at: float
    dev_build_token: Optional[str] = None


class DaemonStatusResponse(BaseModel):
    """Daemon lifecycle status response."""

    lifecycle_initialized: bool = False
    worker_manager_ready: bool = False
    model_load_balancer_ready: bool = False
    loaded_models: List[str] = Field(default_factory=list)
    runtime_registry_ready: bool = False
    embedded_api_server_running: bool = False
    preloaded_model_path: Optional[str] = None


# Track server start time
_start_time = time.time()
_start_pid = os.getpid()
_start_dev_build_token = current_dev_build_token()


def build_health_payload(status: str) -> Dict[str, Any]:
    """Return shared health metadata for legacy and versioned routes."""
    return {
        "status": status,
        "version": AIRUNNER_VERSION,
        "uptime": time.time() - _start_time,
        "pid": _start_pid,
        "started_at": _start_time,
        "dev_build_token": _start_dev_build_token,
    }


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns server status, version, and uptime.
    """
    return HealthResponse(**build_health_payload("healthy"))


@router.get("/health/daemon", response_model=DaemonStatusResponse)
async def daemon_status(request: Request):
    """Return daemon lifecycle state when available."""
    lifecycle_service = getattr(request.app.state, "lifecycle_service", None)
    if lifecycle_service is None:
        return DaemonStatusResponse()
    return DaemonStatusResponse(**lifecycle_service.get_status())


@router.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "AI Runner API",
        "version": AIRUNNER_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
    }
