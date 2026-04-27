"""Configuration model and persistence for daemon mode."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class DaemonConfig:
    """Configuration for daemon mode."""

    def __init__(self, config_path: Optional[Path] = None):
        """Load daemon configuration from disk or defaults."""
        self.config_path = config_path or self._default_config_path()
        self.config = self._load_config()

    def _default_config_path(self) -> Path:
        """Get default configuration path."""
        if sys.platform == "win32":
            config_dir = Path(os.environ.get("APPDATA", "")) / "airunner"
        else:
            config_dir = Path.home() / ".config" / "airunner"
        return config_dir / "daemon.yaml"

    def _load_config(self) -> Dict[str, Any]:
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

    def _default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
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
                "heartbeat_file": "~/.airunner/daemon_heartbeat",
            },
            "logging": {
                "level": "INFO",
                "file": "~/.airunner/logs/daemon.log",
                "max_bytes": 50 * 1024 * 1024,
                "backup_count": 5,
            },
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