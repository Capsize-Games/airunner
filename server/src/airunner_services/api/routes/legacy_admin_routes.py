"""Legacy compatibility routes for admin controls."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Request

from airunner_services.contract_enums import SignalCode
from airunner_services.utils.application.signal_mediator import SignalMediator

from .legacy_common import queue_service_llm_unload, schedule_process_shutdown
from .legacy_contracts import LegacyInterruptRequest

router = APIRouter()


@router.post("/admin/reset_memory")
def legacy_admin_reset_memory() -> Dict[str, Any]:
    """Return the legacy success payload for reset-memory requests."""
    return {"status": "ok"}


@router.post("/admin/interrupt")
def legacy_admin_interrupt(
    body: Optional[LegacyInterruptRequest] = None,
) -> Dict[str, Any]:
    """Interrupt either process or image work through the legacy route."""
    kind = getattr(body, "kind", None) or "process"
    mediator = SignalMediator()
    if kind == "image":
        mediator.emit_signal(SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL, {})
    else:
        mediator.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL, {})
    return {"status": "ok"}


@router.post("/admin/llm/unload")
def legacy_admin_unload_llm(req: Request) -> Dict[str, Any]:
    """Unload the LLM through either the lifecycle queue or legacy signals."""
    if queue_service_llm_unload(req):
        return {"status": "ok", "queued": True}
    mediator = SignalMediator()
    mediator.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL, {})
    mediator.emit_signal(
        SignalCode.LLM_UNLOAD_SIGNAL,
        {"source": "daemon_admin_unload"},
    )
    return {"status": "ok", "queued": True}


@router.post("/admin/reset_database")
def legacy_admin_reset_database() -> Dict[str, Any]:
    """Return the legacy success payload for reset-database requests."""
    return {"status": "ok"}


@router.post("/admin/shutdown")
def legacy_admin_shutdown() -> Dict[str, Any]:
    """Schedule the current process for shutdown after the response returns."""
    schedule_process_shutdown()
    return {"status": "ok", "shutting_down": True}