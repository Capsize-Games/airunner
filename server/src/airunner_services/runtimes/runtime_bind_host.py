"""Local bind-host policy for model-owned runtime settings."""

from __future__ import annotations

import logging
import os

LOGGER = logging.getLogger(__name__)
DEFAULT_RUNTIME_HOST = "127.0.0.1"


def resolve_runtime_bind_host(*env_names: str) -> str:
    """Return a validated runtime bind host from env overrides."""
    for env_name in env_names:
        value = os.environ.get(env_name, "").strip()
        if value:
            return _validated_bind_host(value)
    return DEFAULT_RUNTIME_HOST


def _validated_bind_host(host: str) -> str:
    """Keep runtime binds local unless remote access was enabled."""
    normalized = host.strip()
    if normalized == "localhost":
        return DEFAULT_RUNTIME_HOST
    if _is_loopback_host(normalized) or _allow_remote_runtime_bind():
        return normalized
    LOGGER.warning("Refusing remote runtime bind host: %s", normalized)
    return DEFAULT_RUNTIME_HOST


def _allow_remote_runtime_bind() -> bool:
    """Return True when remote runtime binds were explicitly enabled."""
    value = os.environ.get("AIRUNNER_ALLOW_REMOTE_RUNTIME_BIND", "0")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_loopback_host(host: str) -> bool:
    """Return True when one host value is loopback-only."""
    return host in {"127.0.0.1", "::1"}


__all__ = ["DEFAULT_RUNTIME_HOST", "resolve_runtime_bind_host"]
