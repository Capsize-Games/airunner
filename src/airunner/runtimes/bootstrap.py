"""Runtime registry bootstrap helpers."""

from typing import Any, Optional

from airunner.runtimes.local_fallback import (
    LocalFallbackArtClient,
    LocalFallbackSTTClient,
    LocalFallbackTTSClient,
    register_local_fallback_clients,
)
from airunner.runtimes.sidecar_llm_client import register_sidecar_llm_client
from airunner.runtimes.sidecar_stt_client import register_sidecar_stt_client
from airunner.runtimes.registry import RuntimeRegistry


def build_runtime_registry(
    app_instance: Optional[Any] = None,
) -> RuntimeRegistry:
    """Build the default runtime registry for the current process."""
    registry = RuntimeRegistry()
    signal_source = app_instance if hasattr(app_instance, "emit_signal") else None
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
    register_sidecar_llm_client(registry)
    register_sidecar_stt_client(registry)
    return registry