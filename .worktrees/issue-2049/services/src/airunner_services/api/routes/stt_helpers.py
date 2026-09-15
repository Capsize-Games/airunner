"""Helper utilities for speech-to-text endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, Request

from airunner_services.ipc.messages import EnvelopeStatus
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import RuntimeKind
from airunner_services.runtimes.registry import RuntimeRegistry


def get_runtime_registry(request: Request) -> Optional[RuntimeRegistry]:
    """Return the runtime registry stored on app state when available."""
    return getattr(request.app.state, "runtime_registry", None)


def require_runtime_registry(request: Request) -> RuntimeRegistry:
    """Return the runtime registry or raise when STT is unavailable."""
    runtime_registry = get_runtime_registry(request)
    if runtime_registry is None:
        raise HTTPException(status_code=503, detail="STT runtime unavailable")
    return runtime_registry


def resolve_stt_client(registry: RuntimeRegistry) -> RuntimeClient:
    """Resolve the configured local STT runtime client."""
    try:
        return registry.resolve(RuntimeKind.STT, provider="local")
    except KeyError as exc:
        raise HTTPException(
            status_code=503, detail="STT runtime unavailable"
        ) from exc


def runtime_error_status(response) -> int:
    """Map runtime envelope failures to HTTP status codes."""
    error = response.error
    if error and error.code.endswith("_timeout"):
        return 504
    return 500


def response_status_is(response: object, expected: EnvelopeStatus) -> bool:
    """Return True when one envelope-like response matches a status."""
    status = getattr(response, "status", None)
    value = getattr(status, "value", status)
    return str(value or "").strip().lower() == expected.value
