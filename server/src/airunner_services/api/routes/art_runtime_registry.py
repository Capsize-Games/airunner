"""Runtime registry helpers for art API routes."""

from typing import Optional

from fastapi import HTTPException, Request

from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import RuntimeKind, RuntimeMode
from airunner_services.runtimes.registry import RuntimeRegistry, RuntimeRoute
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def get_runtime_registry(request: Request) -> Optional[RuntimeRegistry]:
    """Return the runtime registry attached to the FastAPI app."""
    return getattr(request.app.state, "runtime_registry", None)


def require_runtime_registry(request: Request) -> RuntimeRegistry:
    """Return the runtime registry or raise when unavailable."""
    runtime_registry = get_runtime_registry(request)
    if runtime_registry is None:
        raise HTTPException(status_code=503, detail="Art runtime unavailable")
    return runtime_registry


def resolve_art_client(registry: RuntimeRegistry) -> RuntimeClient:
    """Resolve the art runtime client (in-process local fallback)."""
    route = RuntimeRoute(
        RuntimeKind.ART,
        provider="local",
        deployment_mode=RuntimeMode.LOCAL_FALLBACK.value,
    )
    try:
        client = registry.resolve(
            route.runtime,
            provider=route.provider,
            deployment_mode=route.deployment_mode,
        )
    except KeyError:
        raise HTTPException(
            status_code=503, detail="Art runtime unavailable"
        ) from None
    logger.debug(
        "Resolved art runtime client=%s",
        type(client).__name__,
    )
    return client
