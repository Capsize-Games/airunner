import inspect
import logging

from airunner.enums import SignalCode
from airunner.mediator_mixin import MediatorMixin
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


class Logger(
    MediatorMixin
):
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
        MediatorMixin.__init__(self)
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
        self.emit_message(msg, self.DEBUG, "DEBUG")

    def info(self, msg):
        """
        Log info message
        :param msg:
        :return: None
        """
        self.logger.debug(msg)
        self.emit_message(msg, self.INFO, "INFO")

    def warning(self, msg):
        """
        Log warning message
        :param msg:
        :return: None
        """
        self.logger.warning(msg)
        self.emit_message(msg, self.WARNING, "WARNING")

    def error(self, msg):
        """
        Log error message
        :param msg:
        :return: None
        """
        self.logger.error(msg)
        self.emit_message(msg, self.ERROR, "ERROR")

    def emit_message(self, msg, level: int, level_name: str):
        # Get the current frame
        frame = inspect.currentframe().f_back

        # Get the information about the source code from the frame
        pathname = frame.f_code.co_filename
        lineno = frame.f_lineno

        # Create a LogRecord
        record = logging.LogRecord(self.name, level, pathname, lineno, msg, args=None, exc_info=None, func=None)

        # Add the prefix to the record
        record.prefix = self.prefix

        # Format the record
        formatted_message = self.formatter.format(record)

        self.emit_signal(SignalCode.LOG_LOGGED_SIGNAL, {
            "message": formatted_message,
            "level": level_name
        })
