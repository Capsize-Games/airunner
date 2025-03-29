import logging
import traceback


class Logger:
    def __init__(self, name: str, level: int = logging.DEBUG):
        # Configure the logger
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Remove all existing handlers
        if logger.hasHandlers():
            logger.handlers.clear()

        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s - %(funcName)s - %(lineno)d - %(message)s'))
        logger.addHandler(handler)

        # Disable propagation to the root logger
        logger.propagate = False
        self.logger = logger
    
    def debug(self, message: str):
        self.logger.debug(message)
    
    def error(self, message: str):
        traceback.print_stack()
        self.logger.error(message)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def critical(self, message: str):
        self.logger.critical(message)


def get_logger(name: str, level: int = logging.DEBUG) -> Logger:
    return Logger(name=name, level=level)
