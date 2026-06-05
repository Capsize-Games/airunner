"""Runtime abstractions for AIRunner modality execution."""

from importlib import import_module
from typing import Any

_EXPORTS = {
    "ArtDaemonRuntimeSettings": "airunner_services.runtimes.art_daemon_runtime_settings",
    "ArtInvocationResponse": "airunner_services.runtimes.contracts",
    "ArtInvocationRequest": "airunner_services.runtimes.contracts",
    "ChatMessage": "airunner_services.runtimes.contracts",
    "LLMInvocationRequest": "airunner_services.runtimes.contracts",
    "LLMInvocationResponse": "airunner_services.runtimes.contracts",
    "LlamaCppRuntimeSettings": "airunner_services.runtimes.llama_cpp_runtime_settings",
    "LocalFallbackArtClient": "airunner_services.runtimes.local_fallback",
    "LocalFallbackLLMClient": "airunner_services.runtimes.local_fallback",
    "LocalFallbackSTTClient": "airunner_services.runtimes.local_fallback",
    "LocalFallbackTTSClient": "airunner_services.runtimes.local_fallback",
    "MessageRole": "airunner_services.runtimes.contracts",
    "RuntimeRegistrySTTExecutor": "airunner_services.runtimes.runtime_registry_stt_executor",
    "WhisperCppRuntimeSettings": "airunner_services.runtimes.whisper_cpp_runtime_settings",
    "build_runtime_registry": "airunner_services.runtimes.bootstrap",
    "RuntimeAction": "airunner_services.runtimes.contracts",
    "RuntimeClient": "airunner_services.runtimes.base",
    "RuntimeDescriptor": "airunner_services.runtimes.contracts",
    "RuntimeHealth": "airunner_services.runtimes.contracts",
    "RuntimeHealthStatus": "airunner_services.runtimes.contracts",
    "RuntimeKind": "airunner_services.runtimes.contracts",
    "RuntimeMode": "airunner_services.runtimes.contracts",
    "RuntimeRegistry": "airunner_services.runtimes.registry",
    "RuntimeRoute": "airunner_services.runtimes.registry",
    "SidecarLauncher": "airunner_services.runtimes.sidecar_launcher",
    "SidecarArtClient": "airunner_services.runtimes.sidecar_art_client",
    "SidecarArtLauncher": "airunner_services.runtimes.sidecar_art_launcher",
    "SidecarLLMClient": "airunner_services.runtimes.sidecar_llm_client",
    "SidecarSTTClient": "airunner_services.runtimes.sidecar_stt_client",
    "SidecarSTTLauncher": "airunner_services.runtimes.sidecar_stt_launcher",
    "STTInvocationRequest": "airunner_services.runtimes.contracts",
    "STTInvocationResponse": "airunner_services.runtimes.contracts",
    "TTSInvocationRequest": "airunner_services.runtimes.contracts",
    "TTSInvocationResponse": "airunner_services.runtimes.contracts",
    "TTSDaemonRuntimeSettings": "airunner_services.runtimes.tts_daemon_runtime_settings",
    "TransportKind": "airunner_services.runtimes.contracts",
    "register_local_fallback_clients": "airunner_services.runtimes.local_fallback",
    "register_sidecar_art_client": "airunner_services.runtimes.sidecar_art_client",
    "register_sidecar_llm_client": "airunner_services.runtimes.sidecar_llm_client",
    "register_sidecar_stt_client": "airunner_services.runtimes.sidecar_stt_client",
    "register_sidecar_tts_client": "airunner_services.runtimes.sidecar_tts_client",
    "SidecarTTSClient": "airunner_services.runtimes.sidecar_tts_client",
    "SidecarTTSLauncher": "airunner_services.runtimes.sidecar_tts_launcher",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Resolve runtime exports lazily to avoid import-time cycles."""
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    return getattr(module, name)


def __dir__() -> list[str]:
    """Expose the lazily exported runtime symbols for introspection."""
    return sorted(list(globals()) + list(__all__))
