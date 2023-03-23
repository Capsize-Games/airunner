"""
Wrapper functions for logging
"""
import logging


class Logger:
    def __init__(self):
        self.DEBUG = logging.DEBUG
        self.INFO = logging.INFO
        self.WARNING = logging.WARNING
        self.ERROR = logging.ERROR
        self.FATAL = logging.FATAL

        self.logger = logging.getLogger()
        self.stream_handler = logging.StreamHandler()
        self.set_level(logging.DEBUG)
        self.formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(lineno)d")
        self.stream_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.stream_handler)

    def set_level(self, level):
        """
        Set the logging level
        :param level:
        :return: None
        """
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
        self.logger.info(msg)

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


logger = Logger()
