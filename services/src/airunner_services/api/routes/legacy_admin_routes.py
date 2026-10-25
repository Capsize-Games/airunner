"""Legacy compatibility routes for admin controls."""

import os
import secrets
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request

from airunner_common.contract_enums import SignalCode
from airunner_services.utils.application.signal_mediator import SignalMediator

from .legacy_common import queue_service_llm_unload, schedule_process_shutdown
from .legacy_contracts import LegacyInterruptRequest

router = APIRouter()


def _expected_admin_key() -> str:
    """Return the configured destructive-admin key, or "" when unset."""
    return (os.environ.get("AIRUNNER_ADMIN_KEY") or "").strip()


def _require_admin_key(req: Request) -> None:
    """Gate destructive admin ops behind a separate admin credential.

    The general API key (or loopback token) authenticates ordinary API
    use; process-lifetime ops additionally require ``AIRUNNER_ADMIN_KEY``
    via ``X-Admin-Key`` (or a bearer token). Without a configured key
    the op is refused rather than left open.
    """
    expected = _expected_admin_key()
    if not expected:
        raise HTTPException(
            status_code=403, detail="Admin operations are disabled"
        )
    provided = (req.headers.get("x-admin-key") or "").strip()
    if not provided:
        auth = (req.headers.get("authorization") or "").strip()
        if auth.lower().startswith("bearer "):
            provided = auth.split(" ", 1)[-1].strip()
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/admin/reset_memory")
def legacy_admin_reset_memory() -> Dict[str, Any]:
    """Reject reset-memory: no implementation backs the legacy payload."""
    raise HTTPException(status_code=501, detail="Not implemented")


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
    """Reject reset-database: no implementation backs the legacy payload."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/admin/shutdown")
def legacy_admin_shutdown(req: Request) -> Dict[str, Any]:
    """Schedule the current process for shutdown after the response."""
    _require_admin_key(req)
    schedule_process_shutdown()
    return {"status": "ok", "shutting_down": True}
