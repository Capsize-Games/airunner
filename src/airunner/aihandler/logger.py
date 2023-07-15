import logging
from aihandler.settings import LOG_LEVEL


class Logger:
    """
    Wrapper class for logging
    """

    def __init__(self):
        # disable warnings
        import warnings
        warnings.filterwarnings("ignore")

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
        logging.disable(LOG_LEVEL)
        logging.getLogger("lightning").setLevel(logging.WARNING)
        logging.getLogger("lightning_fabric.utilities.seed").setLevel(logging.WARNING)
        self.set_level(self.DEBUG)

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
