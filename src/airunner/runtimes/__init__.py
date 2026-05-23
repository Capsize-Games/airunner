"""Runtime abstractions for AIRunner modality execution."""

from importlib import import_module
from typing import Any

_EXPORTS = {
    "ArtDaemonRuntimeSettings": "airunner.runtimes.art_daemon_runtime_settings",
    "ArtInvocationResponse": "airunner.runtimes.contracts",
    "ArtInvocationRequest": "airunner.runtimes.contracts",
    "ChatMessage": "airunner.runtimes.contracts",
    "LLMInvocationRequest": "airunner.runtimes.contracts",
    "LLMInvocationResponse": "airunner.runtimes.contracts",
    "LlamaCppRuntimeSettings": "airunner.runtimes.llama_cpp_runtime_settings",
    "MessageRole": "airunner.runtimes.contracts",
    "WhisperCppRuntimeSettings": "airunner.runtimes.whisper_cpp_runtime_settings",
    "build_runtime_registry": "airunner.runtimes.bootstrap",
    "RuntimeAction": "airunner.runtimes.contracts",
    "RuntimeClient": "airunner.runtimes.base",
    "RuntimeDescriptor": "airunner.runtimes.contracts",
    "RuntimeHealth": "airunner.runtimes.contracts",
    "RuntimeHealthStatus": "airunner.runtimes.contracts",
    "RuntimeKind": "airunner.runtimes.contracts",
    "RuntimeMode": "airunner.runtimes.contracts",
    "RuntimeRegistry": "airunner.runtimes.registry",
    "RuntimeRoute": "airunner.runtimes.registry",
    "SidecarLauncher": "airunner.runtimes.sidecar_launcher",
    "SidecarArtClient": "airunner.runtimes.sidecar_art_client",
    "SidecarArtExecutor": "airunner.runtimes.sidecar_art_executor",
    "SidecarArtLauncher": "airunner.runtimes.sidecar_art_launcher",
    "SidecarLLMClient": "airunner.runtimes.sidecar_llm_client",
    "SidecarSTTClient": "airunner.runtimes.sidecar_stt_client",
    "SidecarSTTLauncher": "airunner.runtimes.sidecar_stt_launcher",
    "STTInvocationRequest": "airunner.runtimes.contracts",
    "STTInvocationResponse": "airunner.runtimes.contracts",
    "TTSInvocationRequest": "airunner.runtimes.contracts",
    "TTSInvocationResponse": "airunner.runtimes.contracts",
    "TTSDaemonRuntimeSettings": "airunner.runtimes.tts_daemon_runtime_settings",
    "TransportKind": "airunner.runtimes.contracts",
    "register_sidecar_art_client": "airunner.runtimes.sidecar_art_client",
    "register_sidecar_art_executor": "airunner.runtimes.sidecar_art_executor",
    "register_sidecar_llm_client": "airunner.runtimes.sidecar_llm_client",
    "register_sidecar_stt_client": "airunner.runtimes.sidecar_stt_client",
    "register_sidecar_tts_client": "airunner.runtimes.sidecar_tts_client",
    "register_sidecar_tts_executor": "airunner.runtimes.sidecar_tts_executor",
    "SidecarTTSClient": "airunner.runtimes.sidecar_tts_client",
    "SidecarTTSExecutor": "airunner.runtimes.sidecar_tts_executor",
    "SidecarTTSLauncher": "airunner.runtimes.sidecar_tts_launcher",
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