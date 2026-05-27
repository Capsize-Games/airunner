"""Service-owned persisted settings resolver for llama.cpp sidecars."""

from __future__ import annotations

from typing import Any

from airunner_model.runtimes.llama_cpp_runtime_settings import (
    LlamaCppRuntimeSettings,
    resolve_llama_cpp_runtime_settings as _resolve_llama_cpp_runtime_settings,
)


def _load_llm_settings() -> Any:
    """Return persisted LLM settings when the service database is available."""
    try:
        from airunner_services.database.models.llm_generator_settings import (
            LLMGeneratorSettings,
        )

        return LLMGeneratorSettings.objects.first()
    except Exception:
        return None


def _load_path_settings() -> Any:
    """Return persisted path settings when the service database is available."""
    try:
        from airunner_services.database.models.path_settings import (
            PathSettings,
        )

        return PathSettings.objects.first()
    except Exception:
        return None


def resolve_llama_cpp_runtime_settings() -> LlamaCppRuntimeSettings:
    """Resolve llama.cpp settings using persisted service configuration."""
    return _resolve_llama_cpp_runtime_settings(
        llm_settings=_load_llm_settings(),
        path_settings=_load_path_settings(),
    )


__all__ = [
    "LlamaCppRuntimeSettings",
    "resolve_llama_cpp_runtime_settings",
]
