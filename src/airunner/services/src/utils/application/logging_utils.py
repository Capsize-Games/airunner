"""Logging configuration helpers for headless service execution."""

from __future__ import annotations

import functools
import logging
import os
import sys
from typing import Optional

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application.get_logger import (
    _resolve_log_base_path,
    get_logger,
)
from airunner_services.utils.application.log_hygiene import LogHygieneFilter


_NOISY_LOGGERS = (
    "PIL.PngImagePlugin",
    "sqlalchemy.engine",
    "sqlalchemy.engine.Engine",
    "sqlalchemy.orm",
    "sqlalchemy.orm.mapper",
    "sqlalchemy.orm.mapper.Mapper",
    "sqlalchemy.orm.relationships",
    "sqlalchemy.orm.relationships.RelationshipProperty",
    "sqlalchemy.orm.strategies",
    "sqlalchemy.orm.strategies.LazyLoader",
    "sqlalchemy.orm.path_registry",
    "sqlalchemy.pool",
    "sqlalchemy.pool.impl.QueuePool",
    "uvicorn.access",
)


def configure_noisy_loggers() -> None:
    """Raise levels for third-party loggers that flood startup logs."""
    for logger_name in _NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def _get_log_level_from_env() -> int:
    """Get the configured log level from the environment."""
    log_level_str = os.environ.get("AIRUNNER_LOG_LEVEL")
    if log_level_str is None:
        numeric_level = AIRUNNER_LOG_LEVEL
        level_name = logging.getLevelName(numeric_level)
        if level_name.startswith("Level"):
            return logging.DEBUG
        return numeric_level

    try:
        return int(log_level_str)
    except ValueError:
        level = getattr(logging, log_level_str.upper(), None)
        if isinstance(level, int):
            return level
        return logging.DEBUG


def _get_log_file_path(root_logger: logging.Logger) -> Optional[str]:
    """Determine the file log path or disable file logging cleanly."""
    try:
        log_file = os.environ.get(
            "AIRUNNER_LOG_FILE",
            os.path.join(_resolve_log_base_path(), "airunner.log"),
        )
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, mode=0o700, exist_ok=True)
        return log_file
    except PermissionError as exc:
        root_logger.error(
            "Permission denied creating log directory; "
            "file logging disabled: %s",
            exc,
        )
        return None
    except Exception as exc:
        root_logger.error(
            "Error while preparing log directory; "
            "file logging disabled: %s",
            exc,
        )
        return None


def _create_file_handler(
    log_file: str,
    log_level: int,
    formatter: logging.Formatter,
    root_logger: logging.Logger,
) -> None:
    """Create one file handler and attach it to the root logger."""
    try:
        file_handler = logging.FileHandler(log_file, mode="a")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(LogHygieneFilter())
        root_logger.addHandler(file_handler)
        root_logger.info("Logging to file output")
    except PermissionError as exc:
        root_logger.error(
            "Permission denied creating log file; "
            "file logging disabled: %s",
            exc,
        )
    except Exception as exc:
        root_logger.error(
            "Failed to setup file logging: %s. "
            "File logging disabled.",
            exc,
        )


def _setup_file_logging(
    root_logger: logging.Logger,
    log_level: int,
    formatter: logging.Formatter,
) -> None:
    """Configure file logging when explicitly enabled."""
    if os.environ.get("AIRUNNER_SAVE_LOG_TO_FILE", "0") != "1":
        return

    log_file = _get_log_file_path(root_logger)
    if not log_file:
        return
    _create_file_handler(log_file, log_level, formatter, root_logger)


def configure_headless_logging() -> None:
    """Configure root logging for daemon and headless execution."""
    log_level = _get_log_level_from_env()
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(LogHygieneFilter())
    root_logger.addHandler(stdout_handler)

    _setup_file_logging(root_logger, log_level, formatter)

    try:
        for logger_obj in list(logging.root.manager.loggerDict.values()):
            if not isinstance(logger_obj, logging.Logger):
                continue
            if logger_obj is root_logger:
                continue
            for handler in list(logger_obj.handlers):
                try:
                    logger_obj.removeHandler(handler)
                except Exception:
                    pass
            try:
                logger_obj.propagate = True
                logger_obj.setLevel(log_level)
            except Exception:
                pass
    except Exception:
        pass

    configure_noisy_loggers()
    root_logger.info(
        "Logging configured at %s level",
        logging.getLevelName(log_level),
    )


def log_method_entry_exit(method):
    """Log entry and exit around one instance method."""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        active_logger = getattr(self, "logger", None) or get_logger(
            __name__,
            AIRUNNER_LOG_LEVEL,
        )
        method_name = method.__qualname__
        active_logger.debug("Entering %s", method_name)
        try:
            result = method(self, *args, **kwargs)
        except Exception:
            active_logger.debug("Exiting %s", method_name)
            raise
        active_logger.debug("Exiting %s", method_name)
        return result

    return wrapper


__all__ = [
    "configure_headless_logging",
    "configure_noisy_loggers",
    "log_method_entry_exit",
]
