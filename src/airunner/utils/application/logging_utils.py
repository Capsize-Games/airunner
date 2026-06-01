import functools
import logging
import os
from typing import Optional

from airunner.settings import AIRUNNER_BASE_PATH
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.utils.application.log_hygiene import LogHygieneFilter

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

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
    """Get log level from environment variable."""
    log_level_str = os.environ.get("AIRUNNER_LOG_LEVEL", None)
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
    """Determine the log file path."""
    try:
        base_path = AIRUNNER_BASE_PATH
    except Exception:
        base_path = AIRUNNER_BASE_PATH

    try:
        log_file = os.environ.get(
            "AIRUNNER_LOG_FILE",
            os.path.join(os.path.expanduser(base_path), "airunner.log"),
        )
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        return log_file
    except PermissionError as e:
        root_logger.error(
            "Permission denied creating log directory; "
            "file logging disabled: %s",
            e,
        )
        return None
    except Exception as e:
        root_logger.error(
            "Error while preparing log directory; "
            "file logging disabled: %s",
            e,
        )
        return None


def _create_file_handler(
    log_file: str,
    log_level: int,
    formatter: logging.Formatter,
    root_logger: logging.Logger,
) -> None:
    """Create and add file handler to logger."""
    try:
        file_handler = logging.FileHandler(log_file, mode="a")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(LogHygieneFilter())
        root_logger.addHandler(file_handler)
        root_logger.info("Logging to file output")
    except PermissionError as e:
        root_logger.error(
            "Permission denied creating log file; "
            "file logging disabled: %s",
            e,
        )
    except Exception as e:
        root_logger.error(
            "Failed to setup file logging: %s. "
            "File logging disabled.",
            e,
        )


def _setup_file_logging(
    root_logger: logging.Logger, log_level: int, formatter: logging.Formatter
) -> None:
    """Setup file logging if enabled."""
    if os.environ.get("AIRUNNER_SAVE_LOG_TO_FILE", "0") != "1":
        return

    log_file = _get_log_file_path(root_logger)
    if not log_file:
        return
    _create_file_handler(log_file, log_level, formatter, root_logger)


def log_method_entry_exit(method):
    """
    Decorator to log entry and exit of a method using the instance's
    logger if available. Logs exit even if an exception is raised.
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        logger = getattr(self, "logger", None)
        method_name = method.__qualname__
        if logger:
            logger.debug(f"Entering {method_name}")
        else:
            logger.debug(f"Entering {method_name}")
        try:
            result = method(self, *args, **kwargs)
        except Exception:
            if logger:
                logger.debug(f"Exiting {method_name}")
            else:
                logger.debug(f"Exiting {method_name}")
            raise
        if logger:
            logger.debug(f"Exiting {method_name}")
        else:
            logger.debug(f"Exiting {method_name}")
        return result

    return wrapper
