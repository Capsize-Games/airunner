import unittest

import airunner.facehuggershield.nullscream as nullscream


class TestBlacklist(unittest.TestCase):
    def test_blacklist_noop(self):
        # Ensure math is not already imported or is removed to test fresh import
        import sys

        if "math" in sys.modules:
            del sys.modules["math"]
        nullscream.activate(blacklist=["math"])
        import math

        self.assertTrue(math.__doc__ == "This is a noop stand-in module.")
        self.assertTrue(hasattr(math, "sin"))
        self.assertTrue(hasattr(math, "adsf"))

    def tearDown(self):
        nullscream.deactivate(blacklist=["math"])


if __name__ == "__main__":
    unittest.main()
