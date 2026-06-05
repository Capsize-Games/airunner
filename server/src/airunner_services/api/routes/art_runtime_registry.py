"""Runtime registry helpers for art API routes."""

import os
from typing import Optional

from fastapi import HTTPException, Request

from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import RuntimeKind, RuntimeMode
from airunner_services.runtimes.registry import RuntimeRegistry, RuntimeRoute
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


# Route resolution


def get_runtime_registry(request: Request) -> Optional[RuntimeRegistry]:
    """Return the runtime registry attached to the FastAPI app."""
    return getattr(request.app.state, "runtime_registry", None)


def require_runtime_registry(request: Request) -> RuntimeRegistry:
    """Return the runtime registry or raise when unavailable."""
    runtime_registry = get_runtime_registry(request)
    if runtime_registry is None:
        raise HTTPException(status_code=503, detail="Art runtime unavailable")
    return runtime_registry


def art_runtime_route() -> tuple[RuntimeRoute, str]:
    """Return the expected art runtime route and missing-route detail."""
    if os.environ.get("AIRUNNER_ART_SIDECAR_PROCESS") == "1":
        route = RuntimeRoute(
            RuntimeKind.ART,
            provider="local",
            deployment_mode=RuntimeMode.LOCAL_FALLBACK.value,
        )
        return route, "Art runtime unavailable"
    route = RuntimeRoute(
        RuntimeKind.ART,
        provider="local",
        deployment_mode=RuntimeMode.SIDECAR.value,
    )
    return route, "Art sidecar runtime unavailable"


def list_route_match(
    registry: RuntimeRegistry,
    route: RuntimeRoute,
) -> bool:
    """Return True when one listed route matches the expected route."""
    normalized = route.normalized()
    return any(
        candidate.normalized() == normalized
        for candidate in registry.list_routes()
    )


def resolved_route_exists(
    registry: RuntimeRegistry,
    route: RuntimeRoute,
) -> bool:
    """Return True when the registry can resolve one route directly."""
    try:
        registry.resolve(
            route.runtime,
            provider=route.provider,
            deployment_mode=route.deployment_mode,
        )
    except KeyError:
        return False
    return True


def has_runtime_route(
    registry: RuntimeRegistry,
    route: RuntimeRoute,
) -> bool:
    """Return True when one exact runtime route is registered."""
    has_route = getattr(registry, "has_route", None)
    if callable(has_route):
        return bool(has_route(route))
    list_routes = getattr(registry, "list_routes", None)
    if callable(list_routes):
        return list_route_match(registry, route)
    return resolved_route_exists(registry, route)


def resolve_art_client(registry: RuntimeRegistry) -> RuntimeClient:
    """Resolve the art runtime client for the current daemon role."""
    route, detail = art_runtime_route()
    if not has_runtime_route(registry, route):
        raise HTTPException(status_code=503, detail=detail)
    client = registry.resolve(
        route.runtime,
        provider=route.provider,
        deployment_mode=route.deployment_mode,
    )
    logger.debug(
        "Resolved art runtime route=%s client=%s",
        route.deployment_mode,
        type(client).__name__,
    )
    return client
