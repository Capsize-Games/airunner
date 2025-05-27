import unittest

import airunner.facehuggershield.nullscream as nullscream


class TestWhitelist(unittest.TestCase):
    def _skip_if_pytest(self):
        import sys

        if any("pytest" in mod for mod in sys.modules):
            self.skipTest("NoopLoader import hook is not compatible with pytest.")

    def test_whitelist_noop(self):
        self._skip_if_pytest()
        import sys

        if "requests" in sys.modules:
            del sys.modules["requests"]
        if "math" in sys.modules:
            del sys.modules["math"]
        nullscream.activate(whitelist=["math"], blacklist=["requests"])
        import requests

        self.assertTrue(requests.__doc__ == "This is a noop stand-in module.")
        self.assertTrue(hasattr(requests, "path"))

        import math

        self.assertFalse(math.__doc__ == "This is a noop stand-in module.")
        self.assertTrue(hasattr(math, "sin"))
        self.assertFalse(hasattr(math, "asdf"))

    def tearDown(self):
        nullscream.deactivate(blacklist=["requests"])


if __name__ == "__main__":
    unittest.main()
