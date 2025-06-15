import threading
import logging
from typing import List

from airunner.vendor.facehuggershield.shadowlogger.base_tracker import BaseTracker
from airunner.vendor.facehuggershield.shadowlogger.shadowlogger import ShadowLogger
from airunner.vendor.facehuggershield.shadowlogger.singleton import Singleton


class ShadowLoggerManager(metaclass=Singleton):
    def __init__(self, show_stdout: bool = True):
        self.original_handlers = None
        self.lock = threading.Lock()
        self.__shadowlogger = None
        self.__show_stdout = show_stdout
        self.__active = False

    @property
    def shadowlogger(self):
        return self.__shadowlogger

    def activate(
        self, show_stdout: bool = None, trackers: List[BaseTracker] = None
    ):
        self.__show_stdout = (
            show_stdout if show_stdout is not None else self.__show_stdout
        )

        if self.__active:
            self.deactivate()

        self.__shadowlogger = ShadowLogger(
            self.__show_stdout, trackers=trackers
        )

        self.__active = True
        with self.lock:
            # Get the root logger
            root_logger = logging.getLogger()

            # Keep track of the original handlers
            self.original_handlers = root_logger.handlers[:]

            # Remove all existing handlers from the root logger
            for h in root_logger.handlers[:]:
                root_logger.removeHandler(h)

            # Add the InterceptHandler to the root logger
            root_logger.addHandler(self.shadowlogger.intercept_handler)

            # Set the level for the root logger
            root_logger.setLevel(logging.INFO)

            # Prevent propagation of log records to other handlers
            root_logger.propagate = False

    def deactivate(self):
        if not self.__active:
            return
        with self.lock:
            # Get the root logger
            root_logger = logging.getLogger()

            # Remove the InterceptHandler from the root logger
            root_logger.removeHandler(self.shadowlogger.intercept_handler)

            # Restore the original handlers
            for h in self.original_handlers:
                root_logger.addHandler(h)

            # Allow propagation of log records to other handlers
            root_logger.propagate = True

            # Restore the original os.write and socket.send functions
            self.shadowlogger.intercept_handler.restore_original_functions()
