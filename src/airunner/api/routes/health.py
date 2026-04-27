"""
Health check and status endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
import time


router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    uptime: float


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


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns server status, version, and uptime.
    """
    return HealthResponse(
        status="healthy", version="1.0.0", uptime=time.time() - _start_time
    )


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
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }
