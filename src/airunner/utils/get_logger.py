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
        # Get the name of the calling module
        frame = inspect.currentframe().f_back.f_back
        module_name = frame.f_globals["__name__"]
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - ' + module_name + ' - %(funcName)s - %(lineno)d - %(message)s'))
        logger.addHandler(handler)

        # Disable propagation to the root logger
        logger.propagate = False
        self.logger = logger
    
    def debug(self, message: str, *args, **kwargs):
        self.logger.debug(message)
    
    def error(self, message: str, *args, **kwargs):
        traceback.print_stack()
        self.logger.error(message)

    def info(self, message: str, *args, **kwargs):
        self.logger.info(message)

    def warning(self, message: str, *args, **kwargs):
        self.logger.warning(message)

    def critical(self, message: str, *args, **kwargs):
        self.logger.critical(message)


def get_logger(name: str, level: int = logging.DEBUG) -> Logger:
    return Logger(name=name, level=level)
