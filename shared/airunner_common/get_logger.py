"""Canonical AIRunner logger factory shared by the GUI and services layers.

This module is the single implementation of the AIRunner ``Logger`` wrapper and
``get_logger()`` factory (issue #2050). Both ``src/airunner`` and
``services/src/airunner_services`` re-export from here via thin shims, so there
is exactly one ``class Logger`` / ``def get_logger`` body in the repository.

Design rules:

* This is the base layer: it must **not** import ``airunner`` or
  ``airunner_services`` (that would create a package cycle). The services-only
  "resolve the persistent log base path from ``PathSettings``" behaviour is
  injected at startup via :func:`set_log_base_path_resolver`, never
  hard-wired here.
* Behaviour is the union of the two previously duplicated implementations:
  env-var log level, :class:`~airunner_common.logging_utils.LogHygieneFilter`
  on every handler, console handler always, file handler when
  ``AIRUNNER_SAVE_LOG_TO_FILE=1``, ``AIRUNNER_FLATPAK`` /
  ``XDG_DATA_HOME`` handling, ``0o700`` log directory, and a fail-safe when
  handler setup errors.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Callable, Optional

from airunner_common.logging_utils import LogHygieneFilter
from airunner_common.settings import AIRUNNER_BASE_PATH, AIRUNNER_LOG_LEVEL


_LOGGER_CACHE: dict[str, "Logger"] = {}
_LOGGER_CACHE_LOCK = threading.RLock()

# App-specific resolver for the persistent log directory. Registered once at
# startup by the services layer (which reads PathSettings); the GUI process
# does not register one and falls back to the default base path.
_log_base_path_resolver: Optional[Callable[[], str]] = None


def set_log_base_path_resolver(fn: Callable[[], str]) -> None:
    """Register an app-specific resolver for the persistent log dir.

    Called once at startup by the GUI / services layer. The resolver must
    return a filesystem path (the ``PathSettings.base_path`` value in the
    services process); it may raise, in which case the default path is used.
    """
    global _log_base_path_resolver
    _log_base_path_resolver = fn


def _default_log_base_path() -> str:
    """Return the default directory used for AIRunner log files."""
    if os.environ.get("AIRUNNER_FLATPAK") == "1":
        xdg_data_home = os.environ.get(
            "XDG_DATA_HOME",
            os.path.expanduser("~/.local/share"),
        )
        return os.path.join(xdg_data_home, "airunner")
    return AIRUNNER_BASE_PATH


def _resolve_log_base_path() -> str:
    """Return the configured base path for persistent AIRunner logs."""
    if _log_base_path_resolver is not None:
        try:
            return os.path.expanduser(_log_base_path_resolver())
        except Exception:
            pass
    return os.path.expanduser(_default_log_base_path())


def _build_formatter() -> logging.Formatter:
    """Return the default AIRunner log formatter."""
    fmt = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "%(module)s::%(funcName)s - %(lineno)d - %(message)s"
    )
    return logging.Formatter(fmt)


def _configure_console_handler(
    logger: logging.Logger,
    formatter: logging.Formatter,
) -> None:
    """Attach one hygiene-filtered console handler to one logger."""
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(LogHygieneFilter())
    logger.addHandler(console_handler)


def _configure_file_handler(
    logger: logging.Logger,
    formatter: logging.Formatter,
) -> None:
    """Attach one hygiene-filtered file handler when enabled."""
    if os.environ.get("AIRUNNER_SAVE_LOG_TO_FILE", "0") != "1":
        return

    try:
        log_file = os.environ.get(
            "AIRUNNER_LOG_FILE",
            os.path.join(_resolve_log_base_path(), "airunner.log"),
        )
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, mode=0o700, exist_ok=True)

        file_handler = logging.FileHandler(log_file, mode="a")
        file_handler.setFormatter(formatter)
        file_handler.addFilter(LogHygieneFilter())
        logger.addHandler(file_handler)
    except Exception as exc:
        logger.error("Failed to setup file logging: %s", exc)


class Logger:
    """Thin wrapper that preserves AIRunner's cached logger behavior."""

    def __init__(self, name: str, level: int = logging.INFO):
        logger = logging.getLogger(name)
        if getattr(logger, "_airunner_configured", False):
            logger.setLevel(level)
            for handler in logger.handlers:
                handler.setLevel(level)
            self._logger = logger
            self.name = name
            return

        logger.setLevel(level)
        if logger.hasHandlers():
            logger.handlers.clear()
        logger.propagate = False

        formatter = _build_formatter()
        _configure_console_handler(logger, formatter)
        _configure_file_handler(logger, formatter)

        logger.propagate = False
        setattr(logger, "_airunner_configured", True)
        self._logger = logger
        self.name = name

    def _log(self, level: int, method: str, message: str, *args, **kwargs):
        """Log one message without expensive stack inspection."""
        if not self._logger.isEnabledFor(level):
            return

        kwargs.setdefault("stacklevel", 3)
        log_method = getattr(self._logger, method)
        try:
            log_method(message, *args, **kwargs)
        except (TypeError, ValueError) as exc:
            log_method(
                f"[LOGGING ERROR: {exc}] {message} {args}",
                stacklevel=3,
            )

    def isEnabledFor(self, level: int) -> bool:
        """Return whether the wrapped logger is enabled for one level."""
        return self._logger.isEnabledFor(level)

    def debug(self, message: str, *args, **kwargs):
        self._log(logging.DEBUG, "debug", message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        self._log(logging.ERROR, "error", message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs):
        self._log(logging.ERROR, "exception", message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        self._log(logging.INFO, "info", message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        self._log(logging.WARNING, "warning", message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        self._log(logging.CRITICAL, "critical", message, *args, **kwargs)


def get_logger(name: str, level: Optional[int] = None) -> Logger:
    """Return one cached AIRunner logger wrapper."""
    if level is None:
        level = AIRUNNER_LOG_LEVEL
    with _LOGGER_CACHE_LOCK:
        logger = _LOGGER_CACHE.get(name)
        if logger is not None:
            logger._logger.setLevel(level)
            for handler in logger._logger.handlers:
                handler.setLevel(level)
            return logger

        logger = Logger(name=name, level=level)
        _LOGGER_CACHE[name] = logger
        return logger


__all__ = ["Logger", "get_logger", "set_log_base_path_resolver"]
