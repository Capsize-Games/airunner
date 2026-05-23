"""Minimal logger for the model package.

This thin wrapper delegates to Python's standard ``logging`` and
uses the same ``AIRUNNER_LOG_LEVEL`` value as the rest of the
system.  The full hygiene-filtered logger lives in
``airunner_services.utils.application.get_logger`` and is used by
the api / services layers directly.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from airunner_model.settings import AIRUNNER_LOG_LEVEL

_LOGGER_CACHE: dict[str, logging.Logger] = {}
_LOGGER_CACHE_LOCK = threading.RLock()


class Logger:
    """Thin wrapper that provides the expected ``.debug()`` / ``.info()`` interface."""

    def __init__(self, name: str, level: int = logging.INFO):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self.name = name

    def debug(self, message: str, *args, **kwargs):
        self._logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        self._logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        self._logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        self._logger.error(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs):
        self._logger.exception(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        self._logger.critical(message, *args, **kwargs)


def get_logger(name: str, level: Optional[int] = None) -> Logger:
    """Return one cached logger for the model package."""
    if level is None:
        level = AIRUNNER_LOG_LEVEL
    with _LOGGER_CACHE_LOCK:
        logger = _LOGGER_CACHE.get(name)
        if logger is not None:
            logger._logger.setLevel(level)
            return logger
        logger = Logger(name=name, level=level)
        _LOGGER_CACHE[name] = logger
        return logger


__all__ = ["Logger", "get_logger"]
