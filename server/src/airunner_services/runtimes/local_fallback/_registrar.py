"""Local fallback runtime registration helpers."""

from typing import Optional

from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import RuntimeKind, RuntimeMode
from airunner_services.runtimes.registry import RuntimeRegistry, RuntimeRoute
from airunner_services.runtimes.local_fallback._llm_client import (
    LocalFallbackLLMClient,
)
from airunner_services.runtimes.local_fallback._stt_client import (
    LocalFallbackSTTClient,
)
from airunner_services.runtimes.local_fallback._tts_client import (
    LocalFallbackTTSClient,
)
from airunner_services.runtimes.local_fallback._art_client import (
    LocalFallbackArtClient,
)


def register_local_fallback_clients(
    registry: RuntimeRegistry,
    llm_client: Optional[RuntimeClient] = None,
    stt_client: Optional[RuntimeClient] = None,
    tts_client: Optional[RuntimeClient] = None,
    art_client: Optional[RuntimeClient] = None,
    *,
    include_llm: bool = True,
) -> RuntimeRegistry:
    """Register the current local fallback clients in a runtime registry."""
    clients = []
    if include_llm:
        clients.append(llm_client or LocalFallbackLLMClient())
    clients.extend(
        [
            stt_client or LocalFallbackSTTClient(),
            tts_client or LocalFallbackTTSClient(),
            art_client or LocalFallbackArtClient(),
        ]
    )
    for client in clients:
        for route in _local_fallback_routes(
            client.descriptor.runtime,
            client.descriptor.provider,
        ):
            registry.register(route, client)
    return registry


def _local_fallback_routes(
    runtime: RuntimeKind, provider: str
) -> tuple[RuntimeRoute, RuntimeRoute]:
    """Return default and explicit local fallback route aliases."""
    return (
        RuntimeRoute(runtime, provider=provider),
        RuntimeRoute(
            runtime,
            provider=provider,
            deployment_mode=RuntimeMode.LOCAL_FALLBACK.value,
        ),
    )
