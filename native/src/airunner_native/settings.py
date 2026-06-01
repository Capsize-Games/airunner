"""Native-owned launcher settings."""

from __future__ import annotations

import logging
import os


def _env_bool(name: str, default: str = "0") -> bool:
    """Return one boolean environment flag."""
    return os.environ.get(name, default) == "1"


def _get_log_level_from_env() -> int:
    """Resolve the configured Python logging level."""
    log_level_str = os.environ.get("AIRUNNER_LOG_LEVEL", "INFO").upper()
    log_levels = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }
    return log_levels.get(log_level_str, logging.INFO)


AIRUNNER_BASE_PATH = os.path.expanduser(
    os.environ.get("AIRUNNER_BASE_PATH", "~/.local/share/airunner")
)
AIRUNNER_DISABLE_FACEHUGGERSHIELD = _env_bool(
    "AIRUNNER_DISABLE_FACEHUGGERSHIELD",
    "0",
)
AIRUNNER_LOG_LEVEL = _get_log_level_from_env()
LOCAL_SERVER_HOST = os.environ.get("LOCAL_SERVER_HOST", "127.0.0.1")


__all__ = [
    "AIRUNNER_BASE_PATH",
    "AIRUNNER_DISABLE_FACEHUGGERSHIELD",
    "AIRUNNER_LOG_LEVEL",
    "LOCAL_SERVER_HOST",
]