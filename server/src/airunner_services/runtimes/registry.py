"""Runtime client registration and lookup."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

from airunner_services.runtimes.contracts import RuntimeKind
from airunner_services.runtimes.base import RuntimeClient

DEFAULT_PROVIDER = "default"
DEFAULT_DEPLOYMENT = "default"


@dataclass(frozen=True)
class RuntimeRoute:
    """Lookup key for runtime clients."""

    runtime: RuntimeKind
    provider: str = DEFAULT_PROVIDER
    deployment_mode: str = DEFAULT_DEPLOYMENT

    def normalized(self) -> "RuntimeRoute":
        """Normalize empty provider and deployment values."""
        provider = self.provider or DEFAULT_PROVIDER
        deployment_mode = self.deployment_mode or DEFAULT_DEPLOYMENT
        return RuntimeRoute(
            runtime=self.runtime,
            provider=provider,
            deployment_mode=deployment_mode,
        )


class RuntimeRegistry:
    """Registry for daemon-visible runtime clients."""

    def __init__(self) -> None:
        self._clients: Dict[RuntimeRoute, RuntimeClient] = {}

    def register(self, route: RuntimeRoute, client: RuntimeClient) -> None:
        """Register a client under a runtime route."""
        self._clients[route.normalized()] = client

    def has_route(self, route: RuntimeRoute) -> bool:
        """Return True when a route is already registered."""
        return route.normalized() in self._clients

    def list_routes(self) -> Iterable[RuntimeRoute]:
        """Return all registered routes."""
        return tuple(self._clients.keys())

    def resolve(
        self,
        runtime: RuntimeKind,
        provider: str,
        deployment_mode: str = DEFAULT_DEPLOYMENT,
    ) -> RuntimeClient:
        """Resolve a client with explicit fallback order."""
        for route in self._candidate_routes(
            runtime, provider, deployment_mode
        ):
            client = self._clients.get(route)
            if client is not None:
                return client
        runtime_name = runtime.value
        raise KeyError(
            f"No runtime client registered for {runtime_name}/{provider}/"
            f"{deployment_mode}"
        )

    def _candidate_routes(
        self,
        runtime: RuntimeKind,
        provider: str,
        deployment_mode: str,
    ) -> Tuple[RuntimeRoute, ...]:
        """Return the lookup order used during resolution."""
        exact = RuntimeRoute(runtime, provider, deployment_mode).normalized()
        return (
            exact,
            RuntimeRoute(runtime, provider, DEFAULT_DEPLOYMENT),
            RuntimeRoute(runtime, DEFAULT_PROVIDER, deployment_mode),
            RuntimeRoute(runtime, DEFAULT_PROVIDER, DEFAULT_DEPLOYMENT),
        )


__all__ = [
    "DEFAULT_DEPLOYMENT",
    "DEFAULT_PROVIDER",
    "RuntimeRegistry",
    "RuntimeRoute",
]
