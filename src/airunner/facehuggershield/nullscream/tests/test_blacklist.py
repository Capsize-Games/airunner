import unittest

import nullscream


class TestBlacklist(unittest.TestCase):
    def test_blacklist_noop(self):
        nullscream.activate(blacklist=["math"])
        import math
        self.assertTrue(math.__doc__ == "This is a noop stand-in module.")
        self.assertTrue(hasattr(math, "sin"))
        self.assertTrue(hasattr(math, "adsf"))

    def tearDown(self):
        nullscream.deactivate(blacklist=["math"])


if __name__ == "__main__":
    unittest.main()
