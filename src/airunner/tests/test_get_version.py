import os
import unittest
from airunner.utils.get_version import get_version


class TestVersion(unittest.TestCase):
    def test_get_version(self):
        # get version by grepping through setup.py
        expected_version = None
        if os.path.exists("../../setup.py"):
            path = "../../setup.py"
        elif os.path.exists("./setup.py"):
            path = "./setup.py"
        else:
            path = None
        if path:
            with open(path, "r") as f:
                expected_version = f.read()
                expected_version = expected_version.split("version=")[1].split(",")[0].strip()
        if expected_version:
            # remove anything other than numbers and dots
            expected_version = "".join([c for c in expected_version if c in "0123456789."])
        self.assertEqual(get_version(), expected_version)
