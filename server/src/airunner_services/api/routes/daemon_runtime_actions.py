"""Runtime action helpers for daemon route endpoints."""

from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException, Request

from airunner_services.api.models.runtime_route_request import (
    RuntimeRouteRequest,
)
from airunner_services.ipc.messages import (
    EnvelopeStatus,
    RequestEnvelope,
    ResponseEnvelope,
)
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind

from .daemon_runtime_registry import require_runtime_registry


def resolve_runtime_client(
    request: Request,
    runtime: RuntimeKind,
    provider: str,
    deployment_mode: str,
) -> RuntimeClient:
    """Resolve a runtime client or raise when no route is registered."""
    runtime_registry = require_runtime_registry(request)
    try:
        return runtime_registry.resolve(runtime, provider, deployment_mode)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="Runtime route not found",
        ) from exc


def runtime_failure_status(response: ResponseEnvelope) -> int:
    """Map a runtime failure envelope to an HTTP status code."""
    error = response.error
    if error is None:
        return 502
    if error.code.endswith("_timeout"):
        return 504
    if error.code.endswith("_unsupported"):
        return 409
    return 502


def response_status_is(response: object, expected: EnvelopeStatus) -> bool:
    """Return True when one envelope-like response matches a status."""
    status = getattr(response, "status", None)
    value = getattr(status, "value", status)
    return str(value or "").strip().lower() == expected.value


def ensure_success(response: ResponseEnvelope) -> ResponseEnvelope:
    """Raise an HTTP error when a runtime control action fails."""
    if not response_status_is(response, EnvelopeStatus.FAILED):
        return response
    raise HTTPException(
        status_code=runtime_failure_status(response),
        detail=response.error.message if response.error else "Runtime action failed",
    )


def invoke_runtime_action(
    client: RuntimeClient,
    runtime: RuntimeKind,
    action: RuntimeAction,
    route_request: RuntimeRouteRequest,
) -> ResponseEnvelope:
    """Invoke a runtime lifecycle action through the neutral envelope."""
    response = client.invoke(
        RequestEnvelope(
            request_id=route_request.request_id or str(uuid4()),
            runtime=runtime,
            action=action,
            provider=route_request.provider,
            metadata=dict(route_request.metadata or {}),
        )
    )
    return ensure_success(response)


def cancel_runtime_action(
    client: RuntimeClient,
    route_request: RuntimeRouteRequest,
) -> ResponseEnvelope:
    """Cancel a runtime request when the client supports it."""
    request_id = route_request.request_id or str(uuid4())
    try:
        response = client.cancel(request_id)
    except NotImplementedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ensure_success(response)