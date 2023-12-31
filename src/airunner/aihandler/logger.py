import logging
from airunner.aihandler.settings import LOG_LEVEL
import warnings


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

    logger = logging.getLogger("AI Runner")
    stream_handler = logging.StreamHandler()

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(lineno)d")

    @classmethod
    def set_level(cls, level):
        """
        Set the logging level
        :param level:
        :return: None
        """
        if level is None:
            level = logging.DEBUG
        cls.logger.setLevel(level)
        cls.stream_handler.setLevel(level)

    @classmethod
    def debug(cls, msg):
        """
        Log info message
        :param msg:
        :return: None
        """
        cls.logger.debug(msg)

    @classmethod
    def info(cls, msg):
        """
        Log info message
        :param msg:
        :return: None
        """
        cls.logger.info(msg)

    @classmethod
    def warning(cls, msg):
        """
        Log warning message
        :param msg:
        :return: None
        """
        cls.logger.warning(msg)

    @classmethod
    def error(cls, msg):
        """
        Log error message
        :param msg:
        :return: None
        """
        cls.logger.error(msg)


Logger.set_level(logging.DEBUG)
Logger.stream_handler.setFormatter(Logger.formatter)
Logger.logger.addHandler(Logger.stream_handler)
logging.getLogger("lightning").setLevel(logging.WARNING)
logging.getLogger("lightning_fabric.utilities.seed").setLevel(logging.WARNING)
Logger.set_level(LOG_LEVEL)
