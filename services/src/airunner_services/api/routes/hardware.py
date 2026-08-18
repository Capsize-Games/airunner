"""Hardware profiling endpoint for GUI clients."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

# HardwareProfiler imports torch; the profiler is resolved lazily so the API
# server can import in torch-free installs (issue #2054).
_profiler: "HardwareProfiler | None" = None


def _get_profiler() -> "HardwareProfiler":
    """Return the process-wide hardware profiler, resolving it on first use."""
    global _profiler
    if _profiler is None:
        from airunner_services.model_management.hardware_profiler import (
            HardwareProfiler,
        )

        _profiler = HardwareProfiler()
    return _profiler


router = APIRouter()
logger = logging.getLogger(__name__)


class HardwareProfileResponse(BaseModel):
    """Serializable hardware profile for GUI consumption."""

    total_vram_gb: float
    available_vram_gb: float
    total_ram_gb: float
    available_ram_gb: float
    cuda_available: bool
    cuda_compute_capability: tuple[int, int] | None = Field(default=None)
    device_name: str | None = Field(default=None)
    cpu_count: int
    platform: str


@router.get("/hardware", response_model=HardwareProfileResponse)
async def hardware_profile() -> HardwareProfileResponse:
    """Return the current hardware profile from the host machine."""
    profile = _get_profiler().get_profile()
    return HardwareProfileResponse(
        total_vram_gb=profile.total_vram_gb,
        available_vram_gb=profile.available_vram_gb,
        total_ram_gb=profile.total_ram_gb,
        available_ram_gb=profile.available_ram_gb,
        cuda_available=profile.cuda_available,
        cuda_compute_capability=profile.cuda_compute_capability,
        device_name=profile.device_name,
        cpu_count=profile.cpu_count,
        platform=profile.platform,
    )
