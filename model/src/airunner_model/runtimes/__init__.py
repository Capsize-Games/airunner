"""Runtime compatibility surface for the model package."""

from importlib import import_module
from typing import Any

_EXPORTS = {
	"ArtDaemonRuntimeSettings": "airunner_model.runtimes.art_daemon_runtime_settings",
	"ArtInvocationRequest": "airunner_model.contracts",
	"ArtInvocationResponse": "airunner_model.contracts",
	"ChatMessage": "airunner_model.contracts",
	"LLMInvocationRequest": "airunner_model.contracts",
	"LLMInvocationResponse": "airunner_model.contracts",
	"LlamaCppRuntimeSettings": "airunner_model.runtimes.llama_cpp_runtime_settings",
	"MessageRole": "airunner_model.contracts",
	"RuntimeAction": "airunner_model.contracts",
	"RuntimeClient": "airunner_model.runtimes.base",
	"RuntimeDescriptor": "airunner_model.contracts",
	"RuntimeHealth": "airunner_model.contracts",
	"RuntimeHealthStatus": "airunner_model.contracts",
	"RuntimeKind": "airunner_model.contracts",
	"RuntimeMode": "airunner_model.contracts",
	"RuntimeRegistry": "airunner_model.runtimes.registry",
	"RuntimeRoute": "airunner_model.runtimes.registry",
	"STTInvocationRequest": "airunner_model.contracts",
	"STTInvocationResponse": "airunner_model.contracts",
	"SidecarArtClient": "airunner_model.runtimes.sidecar_art_client",
	"SidecarLauncher": "airunner_model.runtimes.sidecar_launcher",
	"SidecarLLMClient": "airunner_model.runtimes.sidecar_llm_client",
	"SidecarSTTClient": "airunner_model.runtimes.sidecar_stt_client",
	"SidecarSTTLauncher": "airunner_model.runtimes.sidecar_stt_launcher",
	"SidecarTTSClient": "airunner_model.runtimes.sidecar_tts_client",
	"TTSDaemonRuntimeSettings": "airunner_model.runtimes.tts_daemon_runtime_settings",
	"TTSInvocationRequest": "airunner_model.contracts",
	"TTSInvocationResponse": "airunner_model.contracts",
	"TransportKind": "airunner_model.contracts",
	"WhisperCppRuntimeSettings": "airunner_model.runtimes.whisper_cpp_runtime_settings",
	"register_sidecar_art_client": "airunner_model.runtimes.sidecar_art_client",
	"register_sidecar_llm_client": "airunner_model.runtimes.sidecar_llm_client",
	"register_sidecar_stt_client": "airunner_model.runtimes.sidecar_stt_client",
	"register_sidecar_tts_client": "airunner_model.runtimes.sidecar_tts_client",
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