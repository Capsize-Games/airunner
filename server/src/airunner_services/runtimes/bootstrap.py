"""Runtime registry bootstrap helpers."""

import os
from typing import Any, Optional

from airunner_services.runtimes.registry import RuntimeRegistry
from airunner_services.runtimes.sidecar_art_client import (
    register_sidecar_art_client,
)
from airunner_services.runtimes.sidecar_llm_client import (
    register_sidecar_llm_client,
)
from airunner_services.runtimes.sidecar_stt_client import (
    register_sidecar_stt_client,
)
from airunner_services.runtimes.sidecar_tts_client import (
    register_sidecar_tts_client,
)
from airunner_services.runtimes.local_fallback import (
    LocalFallbackArtClient,
    LocalFallbackSTTClient,
    LocalFallbackTTSClient,
    register_local_fallback_clients,
)
from airunner_services.runtimes.sidecar_art_client import SidecarArtClient
from airunner_services.runtimes.sidecar_llm_client import SidecarLLMClient
from airunner_services.runtimes.sidecar_stt_client import SidecarSTTClient
from airunner_services.runtimes.sidecar_tts_client import SidecarTTSClient


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
    if os.environ.get("AIRUNNER_LLM_SIDECAR_PROCESS") != "1":
        register_sidecar_llm_client(registry, SidecarLLMClient())
    if os.environ.get("AIRUNNER_STT_SIDECAR_PROCESS") != "1":
        register_sidecar_stt_client(registry, SidecarSTTClient())
    if os.environ.get("AIRUNNER_ART_SIDECAR_PROCESS") != "1":
        register_sidecar_art_client(registry, SidecarArtClient())
    if os.environ.get("AIRUNNER_TTS_SIDECAR_PROCESS") != "1":
        register_sidecar_tts_client(registry, SidecarTTSClient())
    return registry


def _start_sidecar_launcher(client: Any, name: str) -> None:
    """Start the sidecar daemon process in a background thread."""
    launcher = getattr(client, "_launcher", None)
    if launcher is None:
        return
    import logging
    import threading
    log = logging.getLogger(__name__)
    def _start():
        try:
            launcher.start()
            log.info("%s sidecar daemon ready", name)
        except Exception as exc:
            log.error("%s sidecar failed to start: %s", name, exc)
    thread = threading.Thread(target=_start, daemon=True)
    thread.start()