import unittest
import socket
from airunner.facehuggershield.darklock.no_internet_socket import NoInternetSocket
from airunner.facehuggershield.darklock.restrict_network_access import RestrictNetworkAccess


class TestRestrictInternetAccess(unittest.TestCase):
    def setUp(self):
        self.restrictor = RestrictNetworkAccess()

    def test_install(self):
        self.restrictor.activate()
        self.assertEqual(socket.socket, NoInternetSocket)
        self.assertEqual(socket.SocketType, NoInternetSocket)

    def test_uninstall(self):
        self.restrictor.deactivate()
        self.assertNotEqual(socket.socket, NoInternetSocket)
        self.assertNotEqual(socket.SocketType, NoInternetSocket)


if __name__ == '__main__':
    unittest.main()
