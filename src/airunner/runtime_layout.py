"""Shared local-runtime directory and bind policy helpers."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from airunner.settings import AIRUNNER_BASE_PATH


LOGGER = logging.getLogger(__name__)
DEFAULT_RUNTIME_HOST = "127.0.0.1"


@dataclass(frozen=True)
class RuntimeDirectoryLayout:
    """Standardized filesystem layout for local runtimes."""

    base_path: Path
    runtime_root: Path
    config_dir: Path
    log_dir: Path
    socket_dir: Path
    cache_dir: Path
    model_dir: Path

    def ensure_exists(self) -> None:
        """Create the runtime directories with restrictive defaults."""
        for path in self._managed_paths():
            path.mkdir(parents=True, exist_ok=True, mode=0o700)

    def log_file(self, name: str) -> Path:
        """Return the standardized log file path for one runtime."""
        return self.log_dir / f"{name}.log"

    def heartbeat_file(self, name: str) -> Path:
        """Return the standardized heartbeat file path for one runtime."""
        return self.runtime_root / f"{name}.heartbeat"

    def config_file(self, name: str) -> Path:
        """Return the standardized config file path for one runtime."""
        return self.config_dir / f"{name}.yaml"

    def as_config(self) -> dict[str, str]:
        """Return the layout in daemon-config friendly form."""
        return {
            "root": str(self.runtime_root),
            "config_dir": str(self.config_dir),
            "log_dir": str(self.log_dir),
            "socket_dir": str(self.socket_dir),
            "cache_dir": str(self.cache_dir),
            "model_dir": str(self.model_dir),
        }

    def as_environment(
        self,
        config_path: Optional[Path] = None,
    ) -> dict[str, str]:
        """Return environment variables for a process using this layout."""
        huggingface_root = self.cache_dir / "huggingface"
        transformers_root = huggingface_root / "transformers"
        environment = {
            "AIRUNNER_BASE_PATH": str(self.base_path),
            "AIRUNNER_DATA_DIR": str(self.base_path),
            "AIRUNNER_RUNTIME_ROOT": str(self.runtime_root),
            "AIRUNNER_RUNTIME_CONFIG_DIR": str(self.config_dir),
            "AIRUNNER_RUNTIME_LOG_DIR": str(self.log_dir),
            "AIRUNNER_RUNTIME_SOCKET_DIR": str(self.socket_dir),
            "AIRUNNER_CACHE_DIR": str(self.cache_dir),
            "AIRUNNER_MODEL_DIR": str(self.model_dir),
            "XDG_CACHE_HOME": str(self.cache_dir),
            "HF_HOME": str(huggingface_root),
            "TRANSFORMERS_CACHE": str(transformers_root),
        }
        if config_path is not None:
            environment["AIRUNNER_DAEMON_CONFIG"] = str(config_path)
        return environment

    def _managed_paths(self) -> tuple[Path, ...]:
        """Return the paths created for runtime ownership."""
        return (
            self.base_path,
            self.runtime_root,
            self.config_dir,
            self.log_dir,
            self.socket_dir,
            self.cache_dir,
            self.model_dir,
        )


def build_runtime_directory_layout(
    base_path: Optional[str] = None,
) -> RuntimeDirectoryLayout:
    """Resolve the standardized directory layout for local runtimes."""
    resolved_base = _resolve_directory(
        "AIRUNNER_BASE_PATH",
        base_path or AIRUNNER_BASE_PATH,
    )
    runtime_root = _resolve_directory(
        "AIRUNNER_RUNTIME_ROOT",
        str(resolved_base / "runtime"),
    )
    return RuntimeDirectoryLayout(
        base_path=resolved_base,
        runtime_root=runtime_root,
        config_dir=_resolve_directory(
            "AIRUNNER_RUNTIME_CONFIG_DIR",
            str(runtime_root / "configs"),
        ),
        log_dir=_resolve_directory(
            "AIRUNNER_RUNTIME_LOG_DIR",
            str(runtime_root / "logs"),
        ),
        socket_dir=_resolve_directory(
            "AIRUNNER_RUNTIME_SOCKET_DIR",
            str(runtime_root / "sockets"),
        ),
        cache_dir=_resolve_directory(
            "AIRUNNER_CACHE_DIR",
            str(resolved_base / "cache"),
        ),
        model_dir=_resolve_directory(
            "AIRUNNER_MODEL_DIR",
            str(resolved_base / "models"),
        ),
    )


def resolve_runtime_bind_host(*env_names: str) -> str:
    """Return a runtime bind host, falling back to loopback by default."""
    for env_name in env_names:
        value = os.environ.get(env_name, "").strip()
        if value:
            return _validated_bind_host(value)
    return DEFAULT_RUNTIME_HOST


def _resolve_directory(env_name: str, default: str) -> Path:
    """Resolve a directory from one env var or a default path."""
    raw_value = os.environ.get(env_name, default)
    return Path(os.path.expanduser(raw_value)).resolve()


def _validated_bind_host(host: str) -> str:
    """Keep runtime binds local unless an explicit override is present."""
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
    """Return True when a host value resolves to a loopback bind."""
    return host in {"127.0.0.1", "::1"}