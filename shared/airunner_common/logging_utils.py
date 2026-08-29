"""Shared logging configuration helpers for GUI and headless execution."""

from __future__ import annotations

import functools
import hashlib
import logging
import os
import re
import sys
from collections.abc import Mapping
from typing import Any, Optional

from airunner_common.settings import AIRUNNER_BASE_PATH
from airunner_common.settings import AIRUNNER_LOG_LEVEL


# ---------------------------------------------------------------------------
# Log hygiene (kept local so this module has no cross-package import cycle).
# The per-package ``log_hygiene`` modules remain for their own ``get_logger``
# helpers; the filter below is the canonical copy used by shared logging.
# ---------------------------------------------------------------------------
_URL_PATTERN = re.compile(r"https?://[^\s\"'<>),;]+")
_PATH_PATTERN = re.compile(
    r"(?P<path>(?:~|/)[^\s\"'<>),;]+(?:/[^\s\"'<>),;]+)+)"
)


def _summarize_mapping_keys(
    value: Any,
    *,
    label: str = "data",
    max_keys: int = 8,
) -> str:
    """Return one key-only summary for one mapping payload."""
    if not isinstance(value, Mapping):
        return f"{label}_type={type(value).__name__}"

    keys = sorted(str(key) for key in value.keys())
    preview = ", ".join(keys[:max_keys])
    if len(keys) > max_keys:
        preview = f"{preview}, ..."
    return f"{label}_keys=[{preview}]"


def _fingerprint_value(value: str | None, *, label: str = "value") -> str:
    """Return one stable fingerprint for one string without logging it."""
    if not value:
        return f"{label}_present=false"

    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"{label}_hash={digest}"


def _sanitize_log_text(text: str) -> str:
    """Redact URLs and filesystem paths from one log string."""
    sanitized = _URL_PATTERN.sub(
        lambda match: _fingerprint_value(match.group(0), label="url"),
        text,
    )
    return _PATH_PATTERN.sub(
        lambda match: _fingerprint_value(match.group("path"), label="path"),
        sanitized,
    )


def _sanitize_log_value(value: Any) -> Any:
    """Sanitize one log value while preserving basic formatting."""
    if isinstance(value, Mapping):
        return _summarize_mapping_keys(value)

    if isinstance(value, os.PathLike):
        return _fingerprint_value(os.fspath(value), label="path")

    if isinstance(value, bytes):
        return f"bytes_len={len(value)}"

    if isinstance(value, str):
        return _sanitize_log_text(value)

    return value


def _sanitize_log_args(args: Any) -> Any:
    """Sanitize one logging args payload."""
    if isinstance(args, Mapping):
        return {key: _sanitize_log_value(value) for key, value in args.items()}

    if isinstance(args, tuple):
        return tuple(_sanitize_log_value(value) for value in args)

    return _sanitize_log_value(args)


def summarize_text(text: str | None, *, label: str = "text") -> str:
    """Return one length-only summary for one text payload."""
    if not text:
        return f"{label}_chars=0"
    return f"{label}_chars={len(text)}"


def summarize_mapping_keys(
    value: Any,
    *,
    label: str = "data",
    max_keys: int = 8,
) -> str:
    """Return one key-only summary for one mapping payload."""
    return _summarize_mapping_keys(
        value,
        label=label,
        max_keys=max_keys,
    )


def fingerprint_value(
    value: str | None,
    *,
    label: str = "value",
) -> str:
    """Return one stable fingerprint for one string without logging it."""
    return _fingerprint_value(value, label=label)


def sanitize_log_text(text: str) -> str:
    """Redact URLs and filesystem paths from one log string."""
    return _sanitize_log_text(text)


def sanitize_log_value(value: Any) -> Any:
    """Sanitize one log value while preserving basic formatting."""
    return _sanitize_log_value(value)


def sanitize_log_args(args: Any) -> Any:
    """Sanitize one logging args payload."""
    return _sanitize_log_args(args)


class LogHygieneFilter(logging.Filter):
    """Filter log records so common sensitive values do not leak by default."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, Mapping):
            record.msg = _summarize_mapping_keys(record.msg, label="message")
            record.args = ()
            return True

        if isinstance(record.msg, os.PathLike):
            record.msg = _fingerprint_value(
                os.fspath(record.msg),
                label="path",
            )
            record.args = ()
            return True

        if isinstance(record.msg, str):
            record.msg = _sanitize_log_text(record.msg)
            if record.args:
                record.args = _sanitize_log_args(record.args)
            return True

        record.msg = _sanitize_log_text(str(record.msg))
        if record.args:
            record.args = _sanitize_log_args(record.args)
        return True


# ---------------------------------------------------------------------------
# Noisy third-party logger configuration
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Headless root-logger configuration
# ---------------------------------------------------------------------------
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


def _resolve_log_base_path() -> str:
    """Return the configured base path for persistent AIRunner logs.

    Delegates to the injectable resolver in :mod:`airunner_common.get_logger`
    so there is exactly one resolver state for both the root-logger setup here
    and the per-logger ``get_logger`` file handler (issue #2050). The shared
    package never imports ``airunner`` / ``airunner_services``; the services
    process registers its ``PathSettings``-based resolver through
    :func:`airunner_common.get_logger.set_log_base_path_resolver`.
    """
    from airunner_common.get_logger import resolve_log_base_path

    return resolve_log_base_path()


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
        active_logger = getattr(self, "logger", None) or logging.getLogger(
            __name__
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
    "LogHygieneFilter",
    "configure_headless_logging",
    "configure_noisy_loggers",
    "fingerprint_value",
    "log_method_entry_exit",
    "sanitize_log_args",
    "sanitize_log_text",
    "sanitize_log_value",
    "summarize_mapping_keys",
    "summarize_text",
]
