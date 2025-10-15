import logging
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
        # Use the standard LogRecord attributes (module, funcName, lineno)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s"
            )
        )

        logger.addHandler(handler)

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

    def debug(self, message: str, *args, **kwargs):
        self._logger.debug(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        self._logger.error(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs):
        # Use the logger's exception method so exc_info=True is set
        self._logger.exception(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        self._logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        self._logger.warning(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        self._logger.critical(message, *args, **kwargs)


def get_logger(name: str, level: int = logging.DEBUG) -> Logger:
    return Logger(name=name, level=level)
