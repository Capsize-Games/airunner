"""Runtime registry accessors for daemon route endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request

from airunner_services.runtimes.contracts import RuntimeKind


def get_runtime_registry(request: Request) -> Any:
    """Return the runtime registry stored on FastAPI app state."""
    return getattr(request.app.state, "runtime_registry", None)


def require_runtime_registry(request: Request) -> Any:
    """Return the runtime registry or raise when daemon state is missing."""
    runtime_registry = get_runtime_registry(request)
    if runtime_registry is None:
        raise HTTPException(
            status_code=503,
            detail="Runtime registry not available",
        )
    return runtime_registry


def parse_runtime_kind(runtime_name: str) -> RuntimeKind:
    """Parse a runtime path value into a known runtime kind."""
    try:
        return RuntimeKind(runtime_name.lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=404, detail="Runtime not found"
        ) from exc


def route_alias(route: Any) -> str:
    """Return a stable alias label for a registered runtime route."""
    return f"{route.provider}:{route.deployment_mode}"


def client_key(
    client: Any,
) -> tuple[str, str, str, str, str | None]:
    """Return a stable dedupe key for a runtime client descriptor."""
    descriptor = client.descriptor
    return (
        descriptor.runtime.value,
        descriptor.provider,
        descriptor.mode.value,
        descriptor.transport.value,
        descriptor.endpoint,
    )
