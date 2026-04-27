"""Daemon control and runtime status endpoints."""

from __future__ import annotations

from typing import Any, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from airunner.api.routes.health import DaemonStatusResponse
from airunner.ipc.messages import EnvelopeStatus, RequestEnvelope, ResponseEnvelope
from airunner.runtimes.base import RuntimeClient
from airunner.runtimes.contracts import RuntimeAction, RuntimeHealthStatus, RuntimeKind

router = APIRouter()

_ART_MODEL_NAME = "SD"


class RuntimeRouteRequest(BaseModel):
    """Select a registered runtime route for daemon control."""

    provider: str = "local"
    deployment_mode: str = "local_fallback"
    request_id: Optional[str] = None


class RuntimeSummaryResponse(BaseModel):
    """Health and capability summary for one runtime client."""

    runtime: str
    provider: str
    mode: str
    transport: str
    status: str
    loaded: bool = False
    details: str = ""
    supports_streaming: bool = False
    allows_model_control: bool = False
    supports_cancellation: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    route_aliases: List[str] = Field(default_factory=list)


class DaemonRuntimeStatusResponse(BaseModel):
    """Combined daemon lifecycle and runtime summary payload."""

    lifecycle: DaemonStatusResponse
    runtimes: List[RuntimeSummaryResponse] = Field(default_factory=list)


def _get_runtime_registry(request: Request) -> Any:
    """Return the runtime registry stored on FastAPI app state."""
    return getattr(request.app.state, "runtime_registry", None)


def _require_runtime_registry(request: Request) -> Any:
    """Return the runtime registry or raise when daemon state is missing."""
    runtime_registry = _get_runtime_registry(request)
    if runtime_registry is None:
        raise HTTPException(
            status_code=503,
            detail="Runtime registry not available",
        )
    return runtime_registry


def _parse_runtime_kind(runtime_name: str) -> RuntimeKind:
    """Parse a runtime path value into a known runtime kind."""
    try:
        return RuntimeKind(runtime_name.lower())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Runtime not found") from exc


def _route_alias(route: Any) -> str:
    """Return a stable alias label for a registered runtime route."""
    return f"{route.provider}:{route.deployment_mode}"


def _client_key(client: RuntimeClient) -> tuple[str, str, str, str, Optional[str]]:
    """Return a stable dedupe key for a runtime client descriptor."""
    descriptor = client.descriptor
    return (
        descriptor.runtime.value,
        descriptor.provider,
        descriptor.mode.value,
        descriptor.transport.value,
        descriptor.endpoint,
    )


def _loaded_model_names(request: Request) -> set[str]:
    """Return the lifecycle service's loaded model names when available."""
    lifecycle_service = getattr(request.app.state, "lifecycle_service", None)
    if lifecycle_service is None:
        return set()
    status = lifecycle_service.get_status()
    return set(status.get("loaded_models") or [])


def _runtime_loaded(request: Request, runtime: RuntimeKind) -> bool:
    """Return whether the runtime is reported as loaded by lifecycle state."""
    loaded_models = _loaded_model_names(request)
    model_name = _ART_MODEL_NAME if runtime is RuntimeKind.ART else runtime.value.upper()
    return model_name in loaded_models


def _health_fields(
    client: RuntimeClient,
    loaded: bool,
) -> tuple[str, str, dict[str, Any]]:
    """Normalize runtime health values for the daemon status payload."""
    health = client.healthcheck()
    status = health.status.value
    details = health.details
    metadata = dict(health.metadata)

    if health.status is RuntimeHealthStatus.UNKNOWN:
        if loaded:
            status = RuntimeHealthStatus.READY.value
            details = details or "loaded"
            metadata.setdefault("model_status", "loaded")
        else:
            status = RuntimeHealthStatus.STOPPED.value
            details = details or "not loaded"

    return status, details, metadata


def _supports_cancellation(client: RuntimeClient) -> bool:
    """Return whether the runtime client overrides cancellation support."""
    return type(client).cancel is not RuntimeClient.cancel


def _build_runtime_summary(
    request: Request,
    client: RuntimeClient,
    route_aliases: List[str],
) -> RuntimeSummaryResponse:
    """Build a daemon-facing runtime summary for a client."""
    loaded = _runtime_loaded(request, client.descriptor.runtime)
    status, details, metadata = _health_fields(client, loaded)
    descriptor = client.descriptor

    return RuntimeSummaryResponse(
        runtime=descriptor.runtime.value,
        provider=descriptor.provider,
        mode=descriptor.mode.value,
        transport=descriptor.transport.value,
        status=status,
        loaded=loaded,
        details=details,
        supports_streaming=descriptor.supports_streaming,
        allows_model_control=descriptor.allows_model_control,
        supports_cancellation=_supports_cancellation(client),
        metadata=metadata,
        route_aliases=route_aliases,
    )


def _collect_runtime_summaries(request: Request) -> List[RuntimeSummaryResponse]:
    """Collect deduplicated runtime summaries from the registry."""
    runtime_registry = _get_runtime_registry(request)
    if runtime_registry is None:
        return []

    grouped: dict[tuple[str, str, str, str, Optional[str]], dict[str, Any]] = {}
    for route in runtime_registry.list_routes():
        client = runtime_registry.resolve(
            route.runtime,
            route.provider,
            route.deployment_mode,
        )
        key = _client_key(client)
        entry = grouped.setdefault(
            key,
            {"client": client, "route_aliases": []},
        )
        alias = _route_alias(route)
        if alias not in entry["route_aliases"]:
            entry["route_aliases"].append(alias)

    summaries = [
        _build_runtime_summary(
            request,
            entry["client"],
            sorted(entry["route_aliases"]),
        )
        for entry in grouped.values()
    ]
    return sorted(summaries, key=lambda item: (item.runtime, item.provider))


def _resolve_runtime_client(
    request: Request,
    runtime: RuntimeKind,
    provider: str,
    deployment_mode: str,
) -> RuntimeClient:
    """Resolve a runtime client or raise when no route is registered."""
    runtime_registry = _require_runtime_registry(request)
    try:
        return runtime_registry.resolve(runtime, provider, deployment_mode)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Runtime route not found") from exc


def _runtime_failure_status(response: ResponseEnvelope) -> int:
    """Map a runtime failure envelope to an HTTP status code."""
    error = response.error
    if error is None:
        return 502
    if error.code.endswith("_timeout"):
        return 504
    if error.code.endswith("_unsupported"):
        return 409
    return 502


def _ensure_success(response: ResponseEnvelope) -> ResponseEnvelope:
    """Raise an HTTP error when a runtime control action fails."""
    if response.status is not EnvelopeStatus.FAILED:
        return response

    raise HTTPException(
        status_code=_runtime_failure_status(response),
        detail=response.error.message if response.error else "Runtime action failed",
    )


def _invoke_runtime_action(
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
        )
    )
    return _ensure_success(response)


def _cancel_runtime_action(
    client: RuntimeClient,
    route_request: RuntimeRouteRequest,
) -> ResponseEnvelope:
    """Cancel a runtime request when the client supports it."""
    request_id = route_request.request_id or str(uuid4())
    try:
        response = client.cancel(request_id)
    except NotImplementedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _ensure_success(response)


@router.get("/status", response_model=DaemonRuntimeStatusResponse)
async def daemon_runtime_status(request: Request):
    """Return combined lifecycle and runtime status for daemon clients."""
    lifecycle_service = getattr(request.app.state, "lifecycle_service", None)
    lifecycle = DaemonStatusResponse()
    if lifecycle_service is not None:
        lifecycle = DaemonStatusResponse(**lifecycle_service.get_status())

    return DaemonRuntimeStatusResponse(
        lifecycle=lifecycle,
        runtimes=_collect_runtime_summaries(request),
    )


@router.get("/runtimes", response_model=List[RuntimeSummaryResponse])
async def list_runtimes(request: Request):
    """List daemon-visible runtimes and their current health summaries."""
    return _collect_runtime_summaries(request)


@router.get("/runtimes/{runtime_name}", response_model=RuntimeSummaryResponse)
async def get_runtime_status(
    runtime_name: str,
    request: Request,
    provider: str = "local",
    deployment_mode: str = "local_fallback",
):
    """Return the health summary for one resolved runtime route."""
    runtime = _parse_runtime_kind(runtime_name)
    client = _resolve_runtime_client(
        request,
        runtime,
        provider,
        deployment_mode,
    )
    summaries = _collect_runtime_summaries(request)
    expected_alias = f"{provider}:{deployment_mode}"
    for summary in summaries:
        if summary.runtime == runtime.value and expected_alias in summary.route_aliases:
            return summary
    return _build_runtime_summary(request, client, [expected_alias])


@router.post("/runtimes/{runtime_name}/load", response_model=ResponseEnvelope)
async def load_runtime(
    runtime_name: str,
    route_request: RuntimeRouteRequest,
    request: Request,
):
    """Load the configured model for a runtime through the daemon API."""
    runtime = _parse_runtime_kind(runtime_name)
    client = _resolve_runtime_client(
        request,
        runtime,
        route_request.provider,
        route_request.deployment_mode,
    )
    return _invoke_runtime_action(
        client,
        runtime,
        RuntimeAction.LOAD_MODEL,
        route_request,
    )


@router.post("/runtimes/{runtime_name}/unload", response_model=ResponseEnvelope)
async def unload_runtime(
    runtime_name: str,
    route_request: RuntimeRouteRequest,
    request: Request,
):
    """Unload the configured model for a runtime through the daemon API."""
    runtime = _parse_runtime_kind(runtime_name)
    client = _resolve_runtime_client(
        request,
        runtime,
        route_request.provider,
        route_request.deployment_mode,
    )
    return _invoke_runtime_action(
        client,
        runtime,
        RuntimeAction.UNLOAD_MODEL,
        route_request,
    )


@router.post("/runtimes/{runtime_name}/cancel", response_model=ResponseEnvelope)
async def cancel_runtime(
    runtime_name: str,
    route_request: RuntimeRouteRequest,
    request: Request,
):
    """Cancel an active runtime request through the daemon API."""
    runtime = _parse_runtime_kind(runtime_name)
    client = _resolve_runtime_client(
        request,
        runtime,
        route_request.provider,
        route_request.deployment_mode,
    )
    return _cancel_runtime_action(client, route_request)