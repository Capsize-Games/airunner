import logging
import socket

from airunner.settings import LOCAL_SERVER_HOST


class NoInternetSocket(socket.socket):
    """
    A custom socket class that prevents any form of internet connections except for localhost on a specified port.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self.__class__, "allowed_port") or not (
            1 <= self.allowed_port <= 65535
        ):
            raise ConnectionError(
                "No valid allowed_port set. Please use set_allowed_port() to set a valid port."
            )
        self.__init_logger()

    def __init_logger(self):
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler("network_access_attempts.log")
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def connect(self, address):
        """
        Overrides the socket's `connect` method to allow connections only to localhost on a specific port.

        Args:
            address (tuple): A tuple of (host, port)

        Raises:
            ConnectionError: If the connection attempt is to an address other than localhost on the allowed port.
        """
        host, port = address
        if host == LOCAL_SERVER_HOST and port == self.allowed_port:
            super().connect(address)
            self.logger.info(f"Allowed connection to {host} on port {port}.")
        else:
            self.logger.info(
                f"Blocked connection attempt to {host} on port {port}."
            )
            raise ConnectionError(
                f"Connection to {host} on port {port} is not allowed."
            )

    @classmethod
    def set_allowed_port(cls, port):
        cls.allowed_port = port
