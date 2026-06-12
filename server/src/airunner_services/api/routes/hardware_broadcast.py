"""Server-driven hardware-stats broadcaster.

VRAM/RAM usage changes continuously and has no discrete "changed" signal,
so it is the one piece of telemetry that genuinely has to be sampled on a
timer. Rather than have every client poll ``GET /api/v1/daemon/hardware``
several times a second, the server samples once and pushes the result to all
subscribers of the ``hardware`` event over the unified ``/api/v1/events``
socket. The loop stays idle whenever no client is listening.
"""

from __future__ import annotations

import asyncio
import logging

from airunner_services.api.routes.events_bus import WsEventBus
from airunner_services.api.routes.events_rpc import EVENT_HARDWARE
from airunner_services.api.routes.hardware import _build_profile

logger = logging.getLogger(__name__)

# How often to sample hardware while at least one client is subscribed.
_INTERVAL_SECONDS = 2.0
# How often to wake up and re-check for subscribers while idle.
_IDLE_POLL_SECONDS = 2.0


async def _broadcast_loop() -> None:
    """Sample and broadcast hardware stats while clients are subscribed."""
    loop = asyncio.get_running_loop()
    bus = WsEventBus()
    while True:
        try:
            if bus.subscriber_count(EVENT_HARDWARE) == 0:
                # Nobody listening — don't measure the GPU/CPU for nothing.
                await asyncio.sleep(_IDLE_POLL_SECONDS)
                continue
            # Profiling can touch CUDA/psutil; keep it off the event loop.
            profile = await loop.run_in_executor(None, _build_profile)
            profile.pop("type", None)
            bus.broadcast(EVENT_HARDWARE, profile)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.debug("Hardware broadcast iteration failed", exc_info=True)
        await asyncio.sleep(_INTERVAL_SECONDS)


def start_hardware_broadcast() -> asyncio.Task:
    """Launch the broadcast loop as a background task."""
    return asyncio.create_task(_broadcast_loop())
