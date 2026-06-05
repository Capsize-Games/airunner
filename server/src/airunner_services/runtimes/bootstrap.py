"""Runtime registry bootstrap helpers."""

from typing import Any, Optional

from airunner_services.runtimes.registry import RuntimeRegistry
from airunner_services.runtimes.local_fallback import (
    LocalFallbackArtClient,
    LocalFallbackSTTClient,
    LocalFallbackTTSClient,
    register_local_fallback_clients,
)


def build_runtime_registry(
    app_instance: Optional[Any] = None,
) -> RuntimeRegistry:
    """Build the default runtime registry for the current process.

    All runtimes are in-process via local fallback clients.  The
    sidecar-based clients have been retired.
    """
    registry = RuntimeRegistry()
    signal_source = (
        app_instance if hasattr(app_instance, "emit_signal") else None
    )
    register_local_fallback_clients(
        registry,
        include_llm=False,
        stt_client=(
            LocalFallbackSTTClient(signal_source=signal_source)
            if signal_source is not None
            else None
        ),
        tts_client=(
            LocalFallbackTTSClient(signal_source=signal_source)
            if signal_source is not None
            else None
        ),
        art_client=(
            LocalFallbackArtClient(signal_source=signal_source)
            if signal_source is not None
            else None
        ),
    )
    return registry
