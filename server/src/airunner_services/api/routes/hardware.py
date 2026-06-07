"""Hardware profiling endpoint for GUI clients."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from airunner_services.api.routes.events import _rpc_register
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


def _build_profile() -> dict:
    """Build a hardware profile dict for JSON serialization."""
    profile = _profiler.get_profile()
    return {
        "type": "hardware_profile",
        "total_vram_gb": profile.total_vram_gb,
        "available_vram_gb": profile.available_vram_gb,
        "total_ram_gb": profile.total_ram_gb,
        "available_ram_gb": profile.available_ram_gb,
        "cuda_available": profile.cuda_available,
        "device_name": profile.device_name,
        "cpu_count": profile.cpu_count,
        "platform": profile.platform,
        "num_gpus": profile.num_gpus,
    }


@_rpc_register("GET", "/api/v1/daemon/hardware")
async def _rpc_hardware_profile(body: dict, **kw: Any) -> dict[str, Any]:
    """Return the current hardware profile."""
    try:
        profile = _build_profile()
        profile.pop("type", None)
        return {"status": 200, "body": profile}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@router.websocket("/hardware/ws")
async def hardware_profile_websocket(websocket: WebSocket):
    """WebSocket endpoint that pushes hardware profile data every 5 seconds.

    On connect, immediately sends the current profile, then continues
    to push updates until the client disconnects.
    """
    await websocket.accept()
    logger.info("Hardware profile WebSocket connected")

    try:
        while True:
            payload = _build_profile()
            await websocket.send_json(payload)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logger.info("Hardware profile WebSocket disconnected")
    except Exception as exc:
        logger.error("Hardware profile WebSocket error: %s", exc)
        try:
            await websocket.close()
        except Exception:
            logger.debug(
                "Failed to close hardware profile WebSocket "
                "(expected during disconnect races)",
                exc_info=True,
            )
