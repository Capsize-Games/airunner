import unittest
from airunner.facehuggershield.darklock.no_internet_socket import (
    NoInternetSocket,
)


class TestNoInternetSocket(unittest.TestCase):
    def test_init_and_connect_denied(self):
        # Set a dummy allowed port for testing purposes
        NoInternetSocket.set_allowed_port(12345)
        sock = NoInternetSocket()
        with self.assertRaises(ConnectionError):
            # Attempt to connect to a disallowed address
            sock.connect(("8.8.8.8", 53))

    def test_connect_allowed(self):
        allowed_port = 54321
        NoInternetSocket.set_allowed_port(allowed_port)
        sock = NoInternetSocket()
        # This should not raise an error, but we can't actually connect in a unit test easily.
        # We'll trust the logic in connect and that set_allowed_port works.
        # To truly test this, we'd need a mock socket that super().connect calls.
        # For now, we ensure it doesn't raise ConnectionError for localhost and allowed port.
        try:
            # We expect this to fail if it tries to actually connect,
            # but it should pass the NoInternetSocket's check.
            # If it raises ConnectionError, our logic is wrong.
            sock.connect(("127.0.0.1", allowed_port))
        except ConnectionError as e:
            if "is not allowed" in str(e):
                self.fail(
                    "Connection to allowed host/port was unexpectedly blocked by NoInternetSocket logic."
                )
        except Exception:
            # Other connection errors (like connection refused if no server is listening) are fine for this test's scope.
            pass

    def test_connect_missing_args(self):
        # This test is to ensure that if connect is called improperly (e.g. by other code),
        # it still behaves somewhat predictably, though it should ideally rely on type checking.
        sock = NoInternetSocket.__new__(
            NoInternetSocket
        )  # Create an instance without calling __init__
        with self.assertRaises(TypeError):
            sock.connect()  # Missing address argument


if __name__ == "__main__":
    unittest.main()
