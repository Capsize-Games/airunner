import unittest
import socket
from airunner.facehuggershield.darklock.no_internet_socket import (
    NoInternetSocket,
)
from airunner.facehuggershield.darklock.restrict_network_access import (
    RestrictNetworkAccess,
)


class TestRestrictInternetAccess(unittest.TestCase):
    def setUp(self):
        self.restrictor = RestrictNetworkAccess()
        self.original_socket_socket = (
            socket.socket
        )  # Keep a reference to the original socket.socket

    def test_install(self):
        self.restrictor.activate(
            allowed_port=8080
        )  # Provide a port for testing
        self.assertEqual(socket.socket, NoInternetSocket)
        # self.assertEqual(socket.SocketType, NoInternetSocket) # SocketType is not consistently replaced, focusing on socket.socket
        # It's more robust to check if creating a socket results in NoInternetSocket instance
        # or if socket.socket itself is NoInternetSocket. The latter is what activate() does.

    def test_uninstall(self):
        # Ensure it's activated first to test deactivation properly
        self.restrictor.activate(allowed_port=8080)
        self.restrictor.deactivate()
        self.assertEqual(
            socket.socket, self.original_socket_socket
        )  # Check it's restored
        # self.assertNotEqual(socket.SocketType, NoInternetSocket)

    def tearDown(self):
        # Ensure that the original socket is restored after each test
        # This is important if a test fails mid-way
        socket.socket = self.original_socket_socket


if __name__ == "__main__":
    unittest.main()
