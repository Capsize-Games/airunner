import logging
import os
import threading
from typing import Optional

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application.log_hygiene import LogHygieneFilter


_LOGGER_CACHE: dict[str, "Logger"] = {}
_LOGGER_CACHE_LOCK = threading.RLock()


class Logger:
    def __init__(self, name: str, level: int = logging.INFO):
        # Configure the logger
        logger = logging.getLogger(name)
        if getattr(logger, "_airunner_configured", False):
            logger.setLevel(level)
            for handler in logger.handlers:
                handler.setLevel(level)
            self._logger = logger
            self.name = name
            return
        logger.setLevel(level)

        # Remove all existing handlers
        if logger.hasHandlers():
            logger.handlers.clear()
        logger.propagate = False

        # Formatter: timestamp - logger name - level - Caller - message
        fmt = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(module)s::%(funcName)s - %(lineno)d - %(message)s"
        )
        formatter = logging.Formatter(fmt)

        # Add console handler -> send to stdout so systemd captures it when configured
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.addFilter(LogHygieneFilter())
        logger.addHandler(console_handler)

        # Add file handler if enabled
        if os.environ.get("AIRUNNER_SAVE_LOG_TO_FILE", "0") == "1":
            try:
                # Import locally to avoid circular dependency
                from airunner_model.models.path_settings import (
                    PathSettings,
                )

                settings = PathSettings.objects.first()
                if settings:
                    base_path = settings.base_path
                elif os.environ.get("AIRUNNER_FLATPAK") == "1":
                    xdg_data_home = os.environ.get(
                        "XDG_DATA_HOME",
                        os.path.expanduser("~/.local/share")
                    )
                    base_path = os.path.join(xdg_data_home, "airunner")
                else:
                    base_path = "~/.local/share/airunner"
            except (ImportError, Exception):
                # Fallback if PathSettings not available yet (during initialization)
                if os.environ.get("AIRUNNER_FLATPAK") == "1":
                    xdg_data_home = os.environ.get(
                        "XDG_DATA_HOME",
                        os.path.expanduser("~/.local/share")
                    )
                    base_path = os.path.join(xdg_data_home, "airunner")
                else:
                    base_path = "~/.local/share/airunner"

            try:
                log_file = os.environ.get(
                    "AIRUNNER_LOG_FILE",
                    os.path.join(
                        os.path.expanduser(base_path),
                        "airunner.log",
                    ),
                )
                # Ensure log directory exists
                log_dir = os.path.dirname(log_file)
                if log_dir:
                    os.makedirs(log_dir, exist_ok=True)

                file_handler = logging.FileHandler(log_file, mode="a")
                file_handler.setFormatter(formatter)
                file_handler.addFilter(LogHygieneFilter())
                logger.addHandler(file_handler)
            except Exception as e:
                # If file logging fails, just log to console
                logger.error(f"Failed to setup file logging: {e}")

        # Disable propagation to the root logger
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
        except (TypeError, ValueError) as e:
            log_method(
                f"[LOGGING ERROR: {e}] {message} {args}",
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
