import logging
import inspect
import os
from typing import Optional

from airunner.settings import AIRUNNER_LOG_LEVEL


class Logger:
    def __init__(self, name: str, level: int = logging.DEBUG):
        # Configure the logger
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Remove all existing handlers
        if logger.hasHandlers():
            logger.handlers.clear()

        # Formatter: timestamp - logger name - level - Caller - message
        fmt = (
            "%(asctime)s - %(name)s - %(levelname)s - %(caller)s - %(message)s"
        )

        class SafeFormatter(logging.Formatter):
            def format(self, record):
                # Ensure 'caller' is present so formatting never fails
                if not hasattr(record, "caller"):
                    try:
                        record.caller = f"{record.module}::{record.funcName} - {record.lineno}"
                    except Exception:
                        record.caller = "<unknown>::<unknown> - 0"
                return super().format(record)

        # Add console handler -> send to stdout so systemd captures it when configured
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(SafeFormatter(fmt))
        logger.addHandler(console_handler)

        # Add file handler if enabled
        if os.environ.get("AIRUNNER_SAVE_LOG_TO_FILE", "1") == "1":
            try:
                # Import locally to avoid circular dependency
                from airunner.components.settings.data.path_settings import (
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
                file_handler.setFormatter(SafeFormatter(fmt))
                logger.addHandler(file_handler)
            except Exception as e:
                # If file logging fails, just log to console
                console_handler.setFormatter(SafeFormatter(fmt))
                logger.error(f"Failed to setup file logging: {e}")

        # Disable propagation to the root logger
        logger.propagate = False
        self._logger = logger
        self.name = name

    def _get_caller_info(self):
        """Get the caller module name, function name and line number."""
        # This helper is no longer required — rely on LogRecord's built-in
        # attributes (module, funcName, lineno) provided by the logging
        # framework. Keep the method for backward compatibility if other
        # modules call it, but return an empty dict.
        return {}

    def _infer_caller_class_name(self) -> str:
        """Inspect the stack to find the caller's class name (if any).

        Returns the class name if the caller is a method, otherwise returns
        the module name as a fallback.
        """
        try:
            frame = inspect.currentframe()
            # climb out of this helper and the wrapper method to reach the caller
            if frame is None:
                return ""
            caller = frame.f_back.f_back
            if caller is None:
                return ""
            locals_ = caller.f_locals
            if "self" in locals_:
                try:
                    return locals_["self"].__class__.__name__
                except Exception:
                    pass
            if "cls" in locals_:
                try:
                    return locals_["cls"].__name__
                except Exception:
                    pass
            # Fallback to module name
            return caller.f_globals.get("__name__", "")
        except Exception:
            return ""

    def _find_caller(self) -> str:
        """Return formatted caller info 'Class::func - lineno' or 'module::func - lineno'."""
        try:
            for frame_info in inspect.stack()[2:]:
                frame = frame_info.frame
                module = frame.f_globals.get("__name__", "")
                if module == __name__:
                    continue
                func_name = frame_info.function
                lineno = frame_info.lineno
                locals_ = frame.f_locals
                class_name = None
                if "self" in locals_:
                    try:
                        class_name = locals_["self"].__class__.__name__
                    except Exception:
                        class_name = None
                elif "cls" in locals_:
                    try:
                        class_name = locals_["cls"].__name__
                    except Exception:
                        class_name = None

                if class_name:
                    return f"{class_name}::{func_name} - {lineno}"
                return f"{module}::{func_name} - {lineno}"
        except Exception:
            return "<unknown>::<unknown> - 0"

    def debug(self, message: str, *args, **kwargs):
        extra = kwargs.pop("extra", {}) or {}
        extra.setdefault("caller", self._find_caller())
        try:
            self._logger.debug(message, *args, extra=extra, **kwargs)
        except (TypeError, ValueError) as e:
            # Fallback: log the message without formatting
            self._logger.debug(
                f"[LOGGING ERROR: {e}] {message} {args}", extra=extra
            )

    def error(self, message: str, *args, **kwargs):
        extra = kwargs.pop("extra", {}) or {}
        extra.setdefault("caller", self._find_caller())
        try:
            self._logger.error(message, *args, extra=extra, **kwargs)
        except (TypeError, ValueError) as e:
            self._logger.error(
                f"[LOGGING ERROR: {e}] {message} {args}", extra=extra
            )

    def exception(self, message: str, *args, **kwargs):
        # Use the logger's exception method so exc_info=True is set
        extra = kwargs.pop("extra", {}) or {}
        extra.setdefault("caller", self._find_caller())
        try:
            self._logger.exception(message, *args, extra=extra, **kwargs)
        except (TypeError, ValueError) as e:
            self._logger.exception(
                f"[LOGGING ERROR: {e}] {message} {args}", extra=extra
            )

    def info(self, message: str, *args, **kwargs):
        extra = kwargs.pop("extra", {}) or {}
        extra.setdefault("caller", self._find_caller())
        try:
            self._logger.info(message, *args, extra=extra, **kwargs)
        except (TypeError, ValueError) as e:
            self._logger.info(
                f"[LOGGING ERROR: {e}] {message} {args}", extra=extra
            )

    def warning(self, message: str, *args, **kwargs):
        extra = kwargs.pop("extra", {}) or {}
        extra.setdefault("caller", self._find_caller())
        try:
            self._logger.warning(message, *args, extra=extra, **kwargs)
        except (TypeError, ValueError) as e:
            self._logger.warning(
                f"[LOGGING ERROR: {e}] {message} {args}", extra=extra
            )

    def critical(self, message: str, *args, **kwargs):
        extra = kwargs.pop("extra", {}) or {}
        extra.setdefault("caller", self._find_caller())
        try:
            self._logger.critical(message, *args, extra=extra, **kwargs)
        except (TypeError, ValueError) as e:
            self._logger.critical(
                f"[LOGGING ERROR: {e}] {message} {args}", extra=extra
            )


def get_logger(name: str, level: Optional[int] = None) -> Logger:
    if level is None:
        level = AIRUNNER_LOG_LEVEL
    return Logger(name=name, level=level)
