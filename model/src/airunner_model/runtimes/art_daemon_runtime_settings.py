"""Resolve isolated art runtime settings from AIRunner configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from airunner_model.runtimes.runtime_bind_host import (
    resolve_runtime_bind_host,
)


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8190
DEFAULT_REQUEST_TIMEOUT_SECONDS = 10.0
DEFAULT_STARTUP_TIMEOUT_SECONDS = 90.0
DEFAULT_INVOCATION_TIMEOUT_SECONDS = 1800.0
DEFAULT_STATUS_POLL_INTERVAL_SECONDS = 0.10


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
class ArtDaemonRuntimeSettings:
    """Resolved settings for the supervised art daemon runtime."""

    host: str
    port: int
    base_daemon_config_path: Optional[str]
    art_model_path: Optional[str]
    art_model_version: Optional[str]
    art_scheduler: Optional[str]
    startup_timeout_seconds: float
    request_timeout_seconds: float
    invocation_timeout_seconds: float
    status_poll_interval_seconds: float

    @property
    def endpoint(self) -> str:
        """Return the base HTTP endpoint exposed by the art runtime."""
        return f"http://{self.host}:{self.port}"


def resolve_art_daemon_runtime_settings() -> ArtDaemonRuntimeSettings:
    """Resolve art runtime settings from the current environment."""
    return ArtDaemonRuntimeSettings(
        host=resolve_runtime_bind_host(
            "AIRUNNER_ART_RUNTIME_HOST",
            "AIRUNNER_RUNTIME_BIND_HOST",
        ),
        port=_env_int("AIRUNNER_ART_RUNTIME_PORT", DEFAULT_PORT),
        base_daemon_config_path=(
            _env_str("AIRUNNER_ART_RUNTIME_DAEMON_CONFIG")
            or _env_str("AIRUNNER_DAEMON_CONFIG")
        ),
        art_model_path=_env_str("AIRUNNER_ART_MODEL_PATH"),
        art_model_version=_env_str("AIRUNNER_ART_MODEL_VERSION"),
        art_scheduler=_env_str("AIRUNNER_ART_SCHEDULER"),
        startup_timeout_seconds=_env_float(
            "AIRUNNER_ART_RUNTIME_STARTUP_TIMEOUT",
            DEFAULT_STARTUP_TIMEOUT_SECONDS,
        ),
        request_timeout_seconds=_env_float(
            "AIRUNNER_ART_RUNTIME_REQUEST_TIMEOUT",
            DEFAULT_REQUEST_TIMEOUT_SECONDS,
        ),
        invocation_timeout_seconds=_env_float(
            "AIRUNNER_ART_RUNTIME_INVOCATION_TIMEOUT",
            DEFAULT_INVOCATION_TIMEOUT_SECONDS,
        ),
        status_poll_interval_seconds=_env_float(
            "AIRUNNER_ART_RUNTIME_STATUS_POLL_INTERVAL",
            DEFAULT_STATUS_POLL_INTERVAL_SECONDS,
        ),
    )


__all__ = [
    "ArtDaemonRuntimeSettings",
    "resolve_art_daemon_runtime_settings",
]