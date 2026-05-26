"""Shared configuration model and persistence for daemon runtimes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from typing import Optional

import yaml

from airunner_model.runtimes.runtime_layout import (
    build_runtime_directory_layout,
)


logger = logging.getLogger(__name__)


class DaemonConfig:
    """Configuration for daemon mode."""

    def __init__(self, config_path: Optional[Path] = None):
        """Load daemon configuration from disk or defaults."""
        self.config_path = config_path or self._default_config_path()
        self.config = self._load_config()

    def _default_config_path(self) -> Path:
        """Get default configuration path."""
        layout = build_runtime_directory_layout()
        return layout.config_file("daemon")

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from file."""
        if not self.config_path.exists():
            return self._default_config()

        try:
            with open(self.config_path, "r", encoding="utf-8") as handle:
                config = yaml.safe_load(handle) or {}
            return {**self._default_config(), **config}
        except Exception as exc:
            logger.error(
                "Failed to load config from %s: %s",
                self.config_path,
                exc,
            )
            return self._default_config()

    def _default_config(self) -> dict[str, Any]:
        """Get default configuration."""
        layout = build_runtime_directory_layout()
        return {
            "server": {
                "host": "127.0.0.1",
                "port": 8188,
                "enable_cors": True,
                "allowed_origins": [
                    "http://localhost:*",
                    "http://127.0.0.1:*",
                ],
            },
            "models": {
                "persistence_mode": "timeout",
                "timeout_minutes": 30,
                "preload": [],
            },
            "health": {
                "heartbeat_interval": 30,
                "heartbeat_file": str(layout.heartbeat_file("daemon")),
            },
            "logging": {
                "level": "INFO",
                "to_file": False,
                "file": str(layout.log_file("daemon")),
                "max_bytes": 50 * 1024 * 1024,
                "backup_count": 5,
            },
            "runtime": layout.as_config(),
        }

    def save(self) -> None:
        """Save configuration to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as handle:
                yaml.safe_dump(
                    self.config,
                    handle,
                    default_flow_style=False,
                )
        except Exception as exc:
            logger.error(
                "Failed to save config to %s: %s",
                self.config_path,
                exc,
            )


__all__ = ["DaemonConfig"]