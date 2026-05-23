"""Daemon control and runtime status endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Request

from airunner_services.api.models.daemon_runtime_status_response import (
    DaemonRuntimeStatusResponse,
)
from airunner_services.api.models.runtime_route_request import (
    RuntimeRouteRequest,
)
from airunner_services.api.models.runtime_summary_response import (
    RuntimeSummaryResponse,
)
from airunner_services.api.routes.health import DaemonStatusResponse
from airunner_services.api.routes.daemon_helpers import (
    cancel_runtime_action,
    collect_runtime_summaries,
    invoke_runtime_action,
    parse_runtime_kind,
    resolve_runtime_client,
)
from airunner_services.ipc.messages import ResponseEnvelope
from airunner_services.runtimes.contracts import RuntimeAction

router = APIRouter()


@router.get("/status", response_model=DaemonRuntimeStatusResponse)
async def daemon_runtime_status(request: Request):
    """Return combined lifecycle and runtime status for daemon clients."""
    lifecycle_service = getattr(request.app.state, "lifecycle_service", None)
    lifecycle = DaemonStatusResponse()
    if lifecycle_service is not None:
        lifecycle = DaemonStatusResponse(**lifecycle_service.get_status())

    return DaemonRuntimeStatusResponse(
        lifecycle=lifecycle,
        runtimes=collect_runtime_summaries(request),
    )


@router.get("/runtimes", response_model=List[RuntimeSummaryResponse])
async def list_runtimes(request: Request):
    """List daemon-visible runtimes and their current health summaries."""
    return collect_runtime_summaries(request)


@router.get("/runtimes/{runtime_name}", response_model=RuntimeSummaryResponse)
async def get_runtime_status(
    runtime_name: str,
    request: Request,
    provider: str = "local",
    deployment_mode: str = "default",
):
    """Return the health summary for one resolved runtime route."""
    runtime = parse_runtime_kind(runtime_name)
    client = resolve_runtime_client(
        request,
        runtime,
        provider,
        deployment_mode,
    )
    summaries = collect_runtime_summaries(request)
    expected_alias = f"{provider}:{deployment_mode}"
    for summary in summaries:
        if summary.runtime == runtime.value and expected_alias in summary.route_aliases:
            return summary
    from airunner_services.api.routes.daemon_helpers import (
        build_runtime_summary,
    )

    return build_runtime_summary(request, client, [expected_alias])


@router.post("/runtimes/{runtime_name}/load", response_model=ResponseEnvelope)
async def load_runtime(
    runtime_name: str,
    route_request: RuntimeRouteRequest,
    request: Request,
):
    """Load the configured model for a runtime through the daemon API."""
    runtime = parse_runtime_kind(runtime_name)
    client = resolve_runtime_client(
        request,
        runtime,
        route_request.provider,
        route_request.deployment_mode,
    )
    return invoke_runtime_action(
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
    runtime = parse_runtime_kind(runtime_name)
    client = resolve_runtime_client(
        request,
        runtime,
        route_request.provider,
        route_request.deployment_mode,
    )
    return invoke_runtime_action(
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
    runtime = parse_runtime_kind(runtime_name)
    client = resolve_runtime_client(
        request,
        runtime,
        route_request.provider,
        route_request.deployment_mode,
    )
    return cancel_runtime_action(client, route_request)