"""Runtime registry bootstrap helpers."""

import importlib
import os
from typing import Any, Mapping, Optional

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


def muse_art_enabled(
    environ: Optional[Mapping[str, str]] = None,
) -> bool:
    source = os.environ if environ is None else environ
    return bool(source.get("MODEL_API_KEY", "").strip())


def _register_muse_art_client(registry: RuntimeRegistry) -> None:
    if not muse_art_enabled():
        return
    try:
        module = importlib.import_module(
            "airunner_services.runtimes.muse_art_client"
        )
    except (ImportError, ValueError):
        return
    register = getattr(module, "register_muse_art_client", None)
    client_cls = getattr(module, "MuseArtClient", None)
    try:
        if callable(register):
            _call_muse_register(registry, register, client_cls)
            return
        if client_cls is not None:
            _register_muse_direct(registry, client_cls())
    except ValueError:
        return


def _call_muse_register(
    registry: RuntimeRegistry,
    register: Any,
    client_cls: Any,
) -> None:
    if client_cls is None:
        register(registry)
        return
    try:
        register(registry, client_cls())
    except TypeError:
        register(registry)


def _register_muse_direct(
    registry: RuntimeRegistry,
    client: Any,
) -> None:
    from airunner_services.runtimes.contracts import (
        RuntimeKind,
        RuntimeMode,
    )
    from airunner_services.runtimes.registry import RuntimeRoute

    route = RuntimeRoute(
        RuntimeKind.ART,
        provider="muse",
        deployment_mode=RuntimeMode.CLOUD.value,
    )
    registry.register(route, client)


def build_runtime_registry(
    app_instance: Optional[Any] = None,
) -> RuntimeRegistry:
    """Build the default runtime registry for the current process."""
    registry = RuntimeRegistry()
    has_signal = hasattr(app_instance, "emit_signal")
    signal_source = app_instance if has_signal else None
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
    register_sidecar_llm_client(registry, SidecarLLMClient())
    register_sidecar_stt_client(registry, SidecarSTTClient())
    if os.environ.get("AIRUNNER_ART_SIDECAR_PROCESS") != "1":
        register_sidecar_art_client(registry, SidecarArtClient())
    if os.environ.get("AIRUNNER_TTS_SIDECAR_PROCESS") != "1":
        register_sidecar_tts_client(registry, SidecarTTSClient())
    if muse_art_enabled():
        _register_muse_art_client(registry)
    return registry