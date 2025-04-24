import logging
import traceback
import inspect


class Logger:
    def __init__(self, name: str, level: int = logging.DEBUG):
        # Configure the logger
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Remove all existing handlers
        if logger.hasHandlers():
            logger.handlers.clear()

        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(caller_module)s - %(caller_function)s - %(caller_lineno)d - %(message)s"
            )
        )

        logger.addHandler(handler)

        # Disable propagation to the root logger
        logger.propagate = False
        self.logger = logger
        self.name = name

    def _get_caller_info(self):
        """Get the caller module name, function name and line number."""
        frame = (
            inspect.currentframe().f_back.f_back
        )  # Skip this function and the logging method
        module_name = self.name
        func_name = ""
        lineno = 0

        candidate = frame.f_globals.get("__name__", "")
        module_name = candidate
        func_name = frame.f_code.co_name
        lineno = frame.f_lineno

        return {
            "caller_module": module_name,
            "caller_function": func_name,
            "caller_lineno": lineno,
        }

    def debug(self, message: str, *args, **kwargs):
        extra = self._get_caller_info()
        self.logger.debug(message, extra=extra, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        extra = self._get_caller_info()
        self.logger.error(message, extra=extra, *args, **kwargs)
        traceback.print_stack()

    def info(self, message: str, *args, **kwargs):
        extra = self._get_caller_info()
        self.logger.info(message, extra=extra, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        extra = self._get_caller_info()
        self.logger.warning(message, extra=extra, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        extra = self._get_caller_info()
        self.logger.critical(message, extra=extra, *args, **kwargs)


def get_logger(name: str, level: int = logging.DEBUG) -> Logger:
    return Logger(name=name, level=level)
