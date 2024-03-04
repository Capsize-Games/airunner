import logging
from airunner.settings import LOG_LEVEL
import warnings
import time


class PrefixFilter(logging.Filter):
    def __init__(self, prefix=''):
        super().__init__()
        self.prefix = prefix

    def filter(self, record):
        record.prefix = self.prefix
        return True


class Logger:
    """
    Wrapper class for logging
    """

    # disable warnings
    warnings.filterwarnings("ignore")

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    FATAL = logging.FATAL
    
    def __init__(self, *args, **kwargs):
        self.prefix = kwargs.pop("prefix", "")
        self.name = kwargs.pop("name", "AI Runner")
        # Append current time to name to make it unique
        self.name += f'_{time.time()}'
        super().__init__()
        self.logger = logging.getLogger(self.name)
        self.formatter = logging.Formatter("%(asctime)s - AI RUNNER - %(levelname)s - %(prefix)s - %(message)s - %(lineno)d")
        self.stream_handler = logging.StreamHandler()
        self.stream_handler.setFormatter(self.formatter)

        # Add the prefix filter
        self.stream_handler.addFilter(PrefixFilter(self.prefix))

        # Check if StreamHandler is already added
        if not any(isinstance(handler, logging.StreamHandler) for handler in self.logger.handlers):
            self.logger.addHandler(self.stream_handler)

        self.set_level(LOG_LEVEL)
        logging.getLogger("lightning").setLevel(logging.WARNING)
        logging.getLogger("lightning_fabric.utilities.seed").setLevel(logging.WARNING)

    def set_level(self, level):
        """
        Set the logging level
        :param level:
        :return: None
        """
        if level is None:
            level = logging.DEBUG
        self.logger.setLevel(level)
        self.stream_handler.setLevel(level)

    def debug(self, msg):
        """
        Log info message
        :param msg:
        :return: None
        """
        self.logger.debug(msg)

    def info(self, msg):
        """
        Log info message
        :param msg:
        :return: None
        """
        self.logger.debug(msg)

    def warning(self, msg):
        """
        Log warning message
        :param msg:
        :return: None
        """
        self.logger.warning(msg)

    def error(self, msg):
        """
        Log error message
        :param msg:
        :return: None
        """
        self.logger.error(msg)
