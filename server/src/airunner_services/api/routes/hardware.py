"""Hardware profiling endpoint for GUI clients."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from airunner_services.model_management.hardware_profiler import (
    HardwareProfiler,
)

router = APIRouter()
logger = logging.getLogger(__name__)
_profiler = HardwareProfiler()


class HardwareProfileResponse(BaseModel):
    """Serializable hardware profile for GUI consumption."""

    total_vram_gb: float
    available_vram_gb: float
    total_ram_gb: float
    available_ram_gb: float
    cuda_available: bool
    device_name: str | None = Field(default=None)
    cpu_count: int
    platform: str
    num_gpus: int = Field(default=0)


@router.get("/hardware", response_model=HardwareProfileResponse)
async def hardware_profile() -> HardwareProfileResponse:
    """Return the current hardware profile from the host machine."""
    profile = _profiler.get_profile()
    return HardwareProfileResponse(
        total_vram_gb=profile.total_vram_gb,
        available_vram_gb=profile.available_vram_gb,
        total_ram_gb=profile.total_ram_gb,
        available_ram_gb=profile.available_ram_gb,
        cuda_available=profile.cuda_available,
        device_name=profile.device_name,
        cpu_count=profile.cpu_count,
        platform=profile.platform,
        num_gpus=profile.num_gpus,
    )
