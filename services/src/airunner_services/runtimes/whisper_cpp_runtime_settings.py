"""Service-owned persisted settings resolver for whisper.cpp sidecars."""

from __future__ import annotations

from typing import Any

from airunner_model.runtimes.whisper_cpp_runtime_settings import (
    WhisperCppRuntimeSettings,
    resolve_whisper_cpp_runtime_settings as _resolve_whisper_cpp_runtime_settings,
)


def _load_path_settings() -> Any:
    """Return persisted path settings when the service database is available."""
    try:
        from airunner_model.models.path_settings import (
            PathSettings,
        )

        return PathSettings.objects.first()
    except Exception:
        return None


def resolve_whisper_cpp_runtime_settings() -> WhisperCppRuntimeSettings:
    """Resolve whisper.cpp settings using persisted service configuration."""
    return _resolve_whisper_cpp_runtime_settings(
        path_settings=_load_path_settings(),
    )


__all__ = [
    "WhisperCppRuntimeSettings",
    "resolve_whisper_cpp_runtime_settings",
]