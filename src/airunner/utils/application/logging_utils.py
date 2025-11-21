import functools
import logging
import os
import sys
from typing import Optional

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _get_log_level_from_env() -> int:
    """Get log level from environment variable."""
    log_level_str = os.environ.get("AIRUNNER_LOG_LEVEL", None)
    if log_level_str is None:
        # Convert numeric AIRUNNER_LOG_LEVEL into textual form if possible
        numeric_level = AIRUNNER_LOG_LEVEL
        # Map numeric level back to name (e.g., 10 => DEBUG)
        level_name = logging.getLevelName(numeric_level)
        if level_name.startswith("Level"):
            # If it's a custom level or not found, fallback to DEBUG
            return logging.DEBUG
        return numeric_level

    try:
        # Try to convert to int (e.g. "10")
        return int(log_level_str)
    except ValueError:
        # Try to convert to level name (e.g. "DEBUG")
        level = getattr(logging, log_level_str.upper(), None)
        if isinstance(level, int):
            return level
        # Fallback
        return logging.DEBUG


def _get_log_file_path(root_logger: logging.Logger) -> str:
    """Determine the log file path."""
    try:
        # Import locally to avoid circular dependency
        from airunner.components.settings.data.path_settings import (
            PathSettings,
        )

        settings = PathSettings.objects.first()
        base_path = (
            settings.base_path if settings else "~/.local/share/airunner"
        )
    except (ImportError, Exception):
        # Fallback if PathSettings not available yet
        base_path = "~/.local/share/airunner"

    try:
        log_file = os.environ.get(
            "AIRUNNER_LOG_FILE",
            os.path.join(os.path.expanduser(base_path), "airunner.log"),
        )
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        return log_file
    except PermissionError as e:
        root_logger.error(
            f"Permission denied creating log directory {log_dir}: {e}; using fallback /tmp/airunner.log"
        )
        return os.path.join("/tmp", "airunner.log")
    except Exception as e:
        root_logger.error(
            f"Error while preparing log directory {log_dir}: {e}; using fallback /tmp/airunner.log"
        )
        return os.path.join("/tmp", "airunner.log")


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
        root_logger.addHandler(file_handler)
        root_logger.info(f"Logging to file: {log_file}")
    except PermissionError as e:
        root_logger.error(
            f"Permission denied creating log file {log_file}: {e}; falling back to /tmp/airunner.log"
        )
        _try_fallback_file_handler(log_level, formatter, root_logger)
    except Exception as e:
        root_logger.error(f"Failed to setup file logging: {e}")


def _try_fallback_file_handler(
    log_level: int, formatter: logging.Formatter, root_logger: logging.Logger
) -> None:
    """Try to create fallback file handler in /tmp."""
    try:
        fallback = os.path.join("/tmp", "airunner.log")
        file_handler = logging.FileHandler(fallback, mode="a")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        root_logger.info(f"Logging to fallback file: {fallback}")
    except Exception as e_fallback:
        root_logger.error(
            f"Failed to setup fallback file logging: {e_fallback}. File logging disabled."
        )


def _setup_file_logging(
    root_logger: logging.Logger, log_level: int, formatter: logging.Formatter
) -> None:
    """Setup file logging if enabled."""
    if os.environ.get("AIRUNNER_SAVE_LOG_TO_FILE", "1") != "1":
        return

    log_file = _get_log_file_path(root_logger)
    _create_file_handler(log_file, log_level, formatter, root_logger)


def configure_headless_logging():
    """Configure logging for headless/systemd operation.

    Must be called early, before other modules initialize their loggers.
    """
    log_level = _get_log_level_from_env()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Add stdout handler (systemd captures this)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)

    # Setup file logging
    _setup_file_logging(root_logger, log_level, formatter)

    # Reconfigure any existing loggers created earlier (e.g., before
    # headless mode was set). Ensure they propagate to root and do not
    # retain their own handlers which may write to different files.
    try:
        for logger_name, logger_obj in list(
            logging.root.manager.loggerDict.items()
        ):
            # Only operate on Logger instances (skip PlaceHolder)
            if not isinstance(logger_obj, logging.Logger):
                continue
            if logger_obj is root_logger:
                continue
            # Remove any handlers attached directly to the logger
            for handler in list(logger_obj.handlers):
                try:
                    logger_obj.removeHandler(handler)
                except Exception:
                    # Best effort: ignore removal errors
                    pass
            # Ensure logs propagate to root and use same level as root
            try:
                logger_obj.propagate = True
                logger_obj.setLevel(log_level)
            except Exception:
                # Ignore errors while reconfiguring existing loggers
                pass
    except Exception:
        # If this fails, continue gracefully - headless root logging still applies
        pass

    root_logger.info(
        f"Logging configured at {logging.getLevelName(log_level)} level"
    )


def log_method_entry_exit(method):
    """
    Decorator to log entry and exit of a method using the instance's logger if available.
    Logs exit even if an exception is raised.
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
