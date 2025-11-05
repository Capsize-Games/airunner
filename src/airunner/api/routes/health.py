"""
Health check and status endpoints.
"""

from fastapi import APIRouter
from pydantic import BaseModel
import time


router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    uptime: float


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


@router.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "AI Runner API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }
