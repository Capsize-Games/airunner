import socket
import logging

from airunner.vendor.facehuggershield.darklock.no_internet_socket import (
    NoInternetSocket,
)
from airunner.vendor.facehuggershield.darklock.singleton import Singleton


class RestrictNetworkAccess(metaclass=Singleton):
    def __init__(self):
        self.__init_logger()
        self.original_socket = socket.socket

    def __init_logger(self):
        """
        Initializes the logger with a file handler and a specific format.
        """
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def activate(self, allowed_port=None):
        self.logger.info("Activating network restrictions")
        if allowed_port is None:
            self.logger.warning(
                "No allowed port specified. Skipping port restriction."
            )
        else:
            NoInternetSocket.set_allowed_port(allowed_port)
        socket.socket = NoInternetSocket

    def deactivate(self):
        self.logger.info("Deactivating network restrictions")
        socket.socket = self.original_socket
