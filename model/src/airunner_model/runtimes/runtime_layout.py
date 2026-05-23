"""Standardized local runtime directory layout helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from airunner_model.settings import AIRUNNER_BASE_PATH

from airunner_model.runtimes.runtime_bind_host import resolve_runtime_bind_host


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
        """Create managed runtime directories with private defaults."""
        for path in self._managed_paths():
            path.mkdir(parents=True, exist_ok=True, mode=0o700)

    def log_file(self, name: str) -> Path:
        """Return the standardized log path for one runtime."""
        return self.log_dir / f"{name}.log"

    def heartbeat_file(self, name: str) -> Path:
        """Return the standardized heartbeat file for one runtime."""
        return self.runtime_root / f"{name}.heartbeat"

    def config_file(self, name: str) -> Path:
        """Return the standardized config file for one runtime."""
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
        """Return process environment variables for one runtime."""
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


def _resolve_directory(env_name: str, default: str) -> Path:
    """Resolve one directory from an env override or default."""
    raw_value = os.environ.get(env_name, default)
    return Path(os.path.expanduser(raw_value)).resolve()


__all__ = [
    "RuntimeDirectoryLayout",
    "build_runtime_directory_layout",
    "resolve_runtime_bind_host",
]