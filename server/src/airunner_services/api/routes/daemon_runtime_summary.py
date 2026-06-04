"""Runtime summary helpers for daemon route endpoints."""

from __future__ import annotations

from typing import List, Optional

from fastapi import Request

from airunner_services.api.models.runtime_summary_response import (
    RuntimeSummaryResponse,
)
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import RuntimeKind

from .daemon_runtime_health import (
    health_fields,
    infer_loaded_state,
    runtime_loaded,
    supports_cancellation,
)
from .daemon_runtime_registry import (
    client_key,
    get_runtime_registry,
    route_alias,
)


def build_runtime_summary(
    request: Request,
    client: RuntimeClient,
    route_aliases: List[str],
) -> RuntimeSummaryResponse:
    """Build a daemon-facing runtime summary for a client."""
    lifecycle_loaded = runtime_loaded(
        request, client.descriptor.runtime
    )
    status, details, metadata = health_fields(
        request, client, lifecycle_loaded
    )
    loaded = infer_loaded_state(status, metadata, lifecycle_loaded)
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
        supports_cancellation=supports_cancellation(client),
        metadata=metadata,
        route_aliases=route_aliases,
    )


def collect_runtime_summaries(
    request: Request,
) -> List[RuntimeSummaryResponse]:
    """Collect deduplicated runtime summaries from the registry."""
    runtime_registry = get_runtime_registry(request)
    if runtime_registry is None:
        return []
    grouped: dict[
        tuple[str, str, str, str, Optional[str]], dict
    ] = {}
    for route in runtime_registry.list_routes():
        client = runtime_registry.resolve(
            route.runtime, route.provider, route.deployment_mode
        )
        key = client_key(client)
        entry = grouped.setdefault(
            key, {"client": client, "route_aliases": []}
        )
        alias = route_alias(route)
        if alias not in entry["route_aliases"]:
            entry["route_aliases"].append(alias)
    summaries = [
        build_runtime_summary(
            request,
            entry["client"],
            sorted(entry["route_aliases"]),
        )
        for entry in grouped.values()
    ]
    return sorted(
        summaries, key=lambda item: (item.runtime, item.provider)
    )


def summary_matches_route(
    summary: RuntimeSummaryResponse,
    runtime: RuntimeKind,
    provider: str,
    deployment_mode: str,
) -> bool:
    """Return True when one summary matches the requested route."""
    return (
        summary.runtime == runtime.value
        and summary.provider == provider
        and summary.mode == deployment_mode
    )
