import socket
import logging

# Setup basic logging configuration to log all unauthorized network access attempts.
# Logs are stored in 'network_access_attempts.log' with a timestamp and the log level information.
logging.basicConfig(
    filename='network_access_attempts.log',  # Log file name
    level=logging.INFO,  # Logging level set to INFO
    format='%(asctime)s - %(levelname)s - %(message)s'  # Log entry format
)


class NoInternetSocket:
    """
    A custom socket class that prevents any form of internet connections.

    This class overrides the default socket object in Python's socket module to ensure that
    no outgoing or incoming internet connections can be established. Attempting to create
    or use a socket connection will result in a ConnectionError.

    Methods:
        __init__(*args, **kwargs): Constructor for the socket object that raises an error.
        connect(*args, **kwargs): Method that simulates the connect functionality and raises an error.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes a new instance of the socket object and logs the attempt.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Raises:
            ConnectionError: Always thrown to indicate that network connections are disabled.
        """
        logging.info("Socket creation attempted and blocked.")
        raise ConnectionError("This application does not allow internet connections.")

    def connect(self, *args, **kwargs):
        """
        Simulates the behavior of the socket's `connect` method. This override is specifically
        designed to log and block any attempts to establish a connection using the socket object.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Raises:
            ConnectionError: Always thrown to prevent any form of network connection.
        """
        logging.info("Connection attempt blocked.")
        raise ConnectionError("This application does not allow internet connections.")


# Override the default socket class and SocketType with our custom NoInternetSocket class.
# This ensures that all instances of socket creation or connection within the Python environment
# using the standard socket interface are blocked and logged.
socket.socket = NoInternetSocket
socket.SocketType = NoInternetSocket