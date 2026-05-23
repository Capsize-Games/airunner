"""Runtime registry bootstrap helpers."""

import os
from typing import Any, Optional

from airunner.runtimes.registry import RuntimeRegistry
from airunner.runtimes.sidecar_art_client import register_sidecar_art_client
from airunner.runtimes.sidecar_art_executor import register_sidecar_art_executor
from airunner.runtimes.sidecar_llm_client import register_sidecar_llm_client
from airunner.runtimes.sidecar_stt_client import register_sidecar_stt_client
from airunner.runtimes.sidecar_tts_client import register_sidecar_tts_client
from airunner.runtimes.sidecar_tts_executor import register_sidecar_tts_executor


def build_runtime_registry(
    app_instance: Optional[Any] = None,
) -> RuntimeRegistry:
    """Build the default runtime registry for the current process."""
    registry = RuntimeRegistry()
    signal_source = (
        app_instance if hasattr(app_instance, "emit_signal") else None
    )

    # Sidecar clients route requests to subprocess runtimes (main daemon).
    register_sidecar_llm_client(registry)
    register_sidecar_stt_client(registry)

    # Art sidecar: when this process IS the art sidecar, register an
    # in-process executor instead of the HTTP sidecar client.
    if os.environ.get("AIRUNNER_ART_SIDECAR_PROCESS") != "1":
        register_sidecar_art_client(registry)
    else:
        register_sidecar_art_executor(registry)

    # TTS sidecar: same split-sidecar pattern as art.
    if os.environ.get("AIRUNNER_TTS_SIDECAR_PROCESS") != "1":
        register_sidecar_tts_client(registry)
    else:
        register_sidecar_tts_executor(registry)

    return registry
