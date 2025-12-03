import logging
import socket

from airunner.settings import LOCAL_SERVER_HOST


class NoInternetSocket(socket.socket):
    """
    A custom socket class that prevents any form of internet connections.
    
    When allowed_port is set to a valid port (1-65535), allows connections
    only to localhost on that specific port.
    
    When allowed_port is set to -1 or invalid, blocks ALL connections.
    """
    
    # Class-level attribute to track if port was set
    allowed_port = None
    _block_all = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if we should block all connections
        if self.__class__.allowed_port == -1:
            self.__class__._block_all = True
        elif not hasattr(self.__class__, "allowed_port") or self.__class__.allowed_port is None:
            # Port not set - block all connections for safety
            self.__class__._block_all = True
        elif not (1 <= self.__class__.allowed_port <= 65535):
            # Invalid port - block all connections
            self.__class__._block_all = True
        else:
            self.__class__._block_all = False
        self.__init_logger()

    def __init_logger(self):
        self.logger = logging.getLogger(__name__)
        # Use StreamHandler instead of FileHandler to avoid file system issues
        if not self.logger.handlers:
            handler = logging.StreamHandler()
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
        # Block ALL connections if configured to do so
        if self.__class__._block_all:
            self.logger.warning(
                f"Blocked connection attempt to {address} (all network access disabled)."
            )
            raise ConnectionError(
                f"All network connections are blocked. Connection to {address} is not allowed."
            )
        
        host, port = address
        # Allow localhost connections on the allowed port only
        if host in (LOCAL_SERVER_HOST, "127.0.0.1", "localhost") and port == self.__class__.allowed_port:
            super().connect(address)
            self.logger.info(f"Allowed connection to {host} on port {port}.")
        else:
            self.logger.warning(
                f"Blocked connection attempt to {host} on port {port}."
            )
            raise ConnectionError(
                f"Connection to {host} on port {port} is not allowed. Only localhost:{self.__class__.allowed_port} is permitted."
            )

    @classmethod
    def set_allowed_port(cls, port):
        """
        Set the allowed port for connections.
        
        Args:
            port: Port number (1-65535) to allow, or -1 to block all connections.
        """
        cls.allowed_port = port
        cls._block_all = (port == -1 or port is None or not (1 <= port <= 65535))
