"""Model-owned runtime settings."""

from __future__ import annotations

import logging
import os


AIRUNNER_BASE_PATH = os.path.expanduser(
    os.environ.get("AIRUNNER_BASE_PATH", "~/.local/share/airunner")
)

DEV_ENV = os.environ.get("DEV_ENV", "1") == "1"


def _build_default_db_url() -> str:
    """Return the default SQLite database URL."""
    db_name = "airunner.dev.db" if DEV_ENV else "airunner.db"
    db_path = os.path.join(AIRUNNER_BASE_PATH, "data", db_name)
    return f"sqlite:///{db_path}"


AIRUNNER_DB_URL = os.environ.get(
    "AIRUNNER_DATABASE_URL",
    _build_default_db_url(),
)
if not AIRUNNER_DB_URL:
    AIRUNNER_DB_URL = _build_default_db_url()


def get_log_level_from_env() -> int:
    """Resolve the configured Python logging level from the env."""
    log_level_str = os.environ.get(
        "AIRUNNER_LOG_LEVEL", "INFO"
    ).upper()
    log_levels = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }
    return log_levels.get(log_level_str, logging.INFO)


AIRUNNER_LOG_LEVEL = get_log_level_from_env()


__all__ = [
    "AIRUNNER_BASE_PATH",
    "AIRUNNER_DB_URL",
    "AIRUNNER_LOG_LEVEL",
    "DEV_ENV",
    "get_log_level_from_env",
]