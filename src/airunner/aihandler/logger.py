import logging

from airunner.settings import LOG_LEVEL
import warnings
import time


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
    
    def __init__(self, **kwargs):
        prefix = kwargs.pop("prefix", "")
        name = kwargs.pop("name", "AI Runner")
        super().__init__()
        self.logger = logging.getLogger(f"{name}::{prefix}")
        self.set_level(LOG_LEVEL)

    @property
    def date_time(self):
        """
        Get the current date time
        :return: str
        """
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def set_level(self, level):
        """
        Set the logging level
        :param level:
        :return: None
        """
        if level is None:
            level = logging.DEBUG
        self.logger.setLevel(level)

    def debug(self, msg):
        """
        Log info message
        :param msg:
        :return: None
        """
        self.logger.debug(f"{self.date_time} - {msg}")

    def info(self, msg):
        """
        Log info message
        :param msg:
        :return: None
        """
        self.logger.debug(f"{self.date_time} - {msg}")

    def warning(self, msg):
        """
        Log warning message
        :param msg:
        :return: None
        """
        self.logger.warning(f"{self.date_time} - {msg}")

    def error(self, msg):
        """
        Log error message
        :param msg:
        :return: None
        """
        self.logger.error(f"{self.date_time} - {msg}")
