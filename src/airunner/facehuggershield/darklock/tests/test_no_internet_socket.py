import unittest
from darklock.no_internet_socket import NoInternetSocket


class TestNoInternetSocket(unittest.TestCase):
    def test_init(self):
        with self.assertRaises(ConnectionError):
            NoInternetSocket()

    def test_connect(self):
        socket = NoInternetSocket.__new__(NoInternetSocket)  # Create an instance without calling __init__
        with self.assertRaises(ConnectionError):
            socket.connect()


if __name__ == '__main__':
    unittest.main()
