import signal
import functools
import unittest


class TimeoutException(Exception):
    """Exception raised when a test times out."""

    pass


def timeout(seconds=10):
    """
    Decorator to apply a timeout to a test method.

    Args:
        seconds: Number of seconds before timeout
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            def handler(signum, frame):
                raise TimeoutException(f"Test timed out after {seconds} seconds")

            # Set the timeout handler
            original_handler = signal.signal(signal.SIGALRM, handler)
            signal.alarm(seconds)

            try:
                result = func(*args, **kwargs)
            finally:
                # Restore the original handler and cancel alarm
                signal.signal(signal.SIGALRM, original_handler)
                signal.alarm(0)

            return result

        return wrapper

    return decorator


class TestTimeoutCase(unittest.TestCase):
    """Example test case illustrating how to use the timeout decorator."""

    @timeout(5)
    def test_with_timeout(self):
        # This test would normally timeout after 5 seconds
        pass
