"""LLM coordination helpers for art API routes."""

import asyncio
from typing import Optional

from fastapi import HTTPException, Request

from airunner_services.contract_enums import ModelStatus
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
_LLM_ART_BUSY_STATUSES = frozenset(
    {
        ModelStatus.LOADING,
        ModelStatus.LOADED,
        ModelStatus.READY,
    }
)
_LLM_UNLOAD_TIMEOUT_SECONDS = 30.0
_LLM_UNLOAD_POLL_SECONDS = 0.1
_UNLOAD_ERROR = "LLM runtime could not be unloaded for art"


# LLM lifecycle checks


def current_llm_status(req: Request) -> Optional[ModelStatus]:
    """Return the current daemon-owned LLM status when available."""
    lifecycle_service = getattr(req.app.state, "lifecycle_service", None)
    status_getter = getattr(
        lifecycle_service, "current_llm_model_status", None
    )
    if not callable(status_getter):
        return None
    try:
        return status_getter()
    except Exception:
        logger.debug(
            "Failed to read LLM status before art request", exc_info=True
        )
        return None


def llm_blocks_art(req: Request) -> bool:
    """Return True when the daemon still has an active LLM in VRAM."""
    return current_llm_status(req) in _LLM_ART_BUSY_STATUSES


async def wait_for_llm_unload(req: Request) -> bool:
    """Wait briefly for the daemon LLM unload to complete."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + _LLM_UNLOAD_TIMEOUT_SECONDS
    while llm_blocks_art(req):
        if loop.time() >= deadline:
            return False
        await asyncio.sleep(_LLM_UNLOAD_POLL_SECONDS)
    return True


def queue_llm_unload(req: Request, source: str) -> bool:
    """Queue one daemon LLM unload request."""
    lifecycle_service = getattr(req.app.state, "lifecycle_service", None)
    queue_unload = getattr(lifecycle_service, "queue_llm_unload", None)
    if not callable(queue_unload):
        raise HTTPException(status_code=503, detail=_UNLOAD_ERROR)
    logger.info("Queueing LLM unload before art request")
    return bool(queue_unload(source=source))


async def unload_llm_before_art(
    req: Request,
    source: str = "art_request",
) -> None:
    """Release daemon-owned LLM VRAM before starting art work."""
    if not llm_blocks_art(req):
        return
    if not queue_llm_unload(req, source):
        raise HTTPException(status_code=503, detail=_UNLOAD_ERROR)
    if await wait_for_llm_unload(req):
        logger.info("LLM unload completed before art request")
        return
    raise HTTPException(
        status_code=503,
        detail="Timed out waiting for LLM unload before art",
    )
