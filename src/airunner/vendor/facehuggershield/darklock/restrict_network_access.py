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
        self._activated = False

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
        """
        Activate network restrictions.
        
        Args:
            allowed_port: If provided, allow connections only to localhost on this port.
                          If None, block ALL network connections.
        """
        if self._activated:
            self.logger.warning("Network restrictions already activated.")
            return
            
        self.logger.info("Activating network restrictions")
        if allowed_port is not None:
            self.logger.info(f"Allowing connections only to localhost:{allowed_port}")
            NoInternetSocket.set_allowed_port(allowed_port)
        else:
            # Block ALL connections by setting port to -1 (invalid port)
            self.logger.warning("Blocking ALL network connections (no allowed port)")
            NoInternetSocket.set_allowed_port(-1)
        
        socket.socket = NoInternetSocket
        self._activated = True

    def deactivate(self):
        if not self._activated:
            self.logger.debug("Network restrictions not active, nothing to deactivate.")
            return
        self.logger.info("Deactivating network restrictions")
        socket.socket = self.original_socket
        self._activated = False
