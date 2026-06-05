"""Resolve isolated TTS runtime settings from AIRunner configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from airunner_services.runtimes.runtime_bind_host import (
    resolve_runtime_bind_host,
)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8191
DEFAULT_REQUEST_TIMEOUT_SECONDS = 120.0
DEFAULT_STARTUP_TIMEOUT_SECONDS = 90.0


def _env_float(name: str, default: float) -> float:
    """Return a float environment override when one is available."""
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        return default
    try:
        return float(str(value).strip())
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    """Return an integer environment override when one is available."""
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        return default
    try:
        return int(str(value).strip())
    except ValueError:
        return default


def _env_str(name: str) -> Optional[str]:
    """Return a trimmed string override or None when it is unset."""
    value = os.environ.get(name, "").strip()
    return value or None


@dataclass(frozen=True)
class TTSDaemonRuntimeSettings:
    """Resolved settings for the supervised TTS daemon runtime."""

    host: str
    port: int
    base_daemon_config_path: Optional[str]
    tts_model_path: Optional[str]
    tts_model_type: Optional[str]
    startup_timeout_seconds: float
    request_timeout_seconds: float

    @property
    def endpoint(self) -> str:
        """Return the base HTTP endpoint exposed by the TTS runtime."""
        return f"http://{self.host}:{self.port}"


def resolve_tts_daemon_runtime_settings() -> TTSDaemonRuntimeSettings:
    """Resolve TTS runtime settings from the current environment."""
    return TTSDaemonRuntimeSettings(
        host=resolve_runtime_bind_host(
            "AIRUNNER_TTS_RUNTIME_HOST",
            "AIRUNNER_RUNTIME_BIND_HOST",
        ),
        port=_env_int("AIRUNNER_TTS_RUNTIME_PORT", DEFAULT_PORT),
        base_daemon_config_path=(
            _env_str("AIRUNNER_TTS_RUNTIME_DAEMON_CONFIG")
            or _env_str("AIRUNNER_DAEMON_CONFIG")
        ),
        tts_model_path=_env_str("AIRUNNER_TTS_MODEL_PATH"),
        tts_model_type=_env_str("AIRUNNER_TTS_MODEL_TYPE"),
        startup_timeout_seconds=_env_float(
            "AIRUNNER_TTS_RUNTIME_STARTUP_TIMEOUT",
            DEFAULT_STARTUP_TIMEOUT_SECONDS,
        ),
        request_timeout_seconds=_env_float(
            "AIRUNNER_TTS_RUNTIME_REQUEST_TIMEOUT",
            DEFAULT_REQUEST_TIMEOUT_SECONDS,
        ),
    )


__all__ = [
    "TTSDaemonRuntimeSettings",
    "resolve_tts_daemon_runtime_settings",
]
