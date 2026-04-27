"""Runtime abstractions for AIRunner modality execution."""

from importlib import import_module
from typing import Any

_EXPORTS = {
    "ArtInvocationResponse": "airunner.runtimes.contracts",
    "ArtInvocationRequest": "airunner.runtimes.contracts",
    "ChatMessage": "airunner.runtimes.contracts",
    "LLMInvocationRequest": "airunner.runtimes.contracts",
    "LLMInvocationResponse": "airunner.runtimes.contracts",
    "LocalFallbackArtClient": "airunner.runtimes.local_fallback",
    "LocalFallbackLLMClient": "airunner.runtimes.local_fallback",
    "LocalFallbackSTTClient": "airunner.runtimes.local_fallback",
    "LocalFallbackTTSClient": "airunner.runtimes.local_fallback",
    "MessageRole": "airunner.runtimes.contracts",
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
    "STTInvocationRequest": "airunner.runtimes.contracts",
    "STTInvocationResponse": "airunner.runtimes.contracts",
    "TTSInvocationRequest": "airunner.runtimes.contracts",
    "TTSInvocationResponse": "airunner.runtimes.contracts",
    "TransportKind": "airunner.runtimes.contracts",
    "register_local_fallback_clients": "airunner.runtimes.local_fallback",
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