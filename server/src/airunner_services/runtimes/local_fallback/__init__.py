"""Local fallback runtime clients backed by existing signal services."""

from airunner_services.runtimes.local_fallback._base import (
    DEFAULT_PROVIDER,
    DEFAULT_TIMEOUT_SECONDS,
    ProgressCallback,
    LLMRequestFactory,
    HealthProvider,
    _SignalRuntimeClient,
)
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
from airunner_services.runtimes.local_fallback._registrar import (
    register_local_fallback_clients,
    _local_fallback_routes,
)

__all__ = [
    "DEFAULT_PROVIDER",
    "DEFAULT_TIMEOUT_SECONDS",
    "ProgressCallback",
    "LLMRequestFactory",
    "HealthProvider",
    "_SignalRuntimeClient",
    "LocalFallbackLLMClient",
    "LocalFallbackSTTClient",
    "LocalFallbackTTSClient",
    "LocalFallbackArtClient",
    "register_local_fallback_clients",
    "_local_fallback_routes",
]
