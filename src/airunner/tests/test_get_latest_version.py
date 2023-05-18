import unittest
from airunner.utils import get_latest_version


class TestVersion(unittest.TestCase):
    def test_get_latest_version(self):
        self.assertEqual(get_latest_version(), "1.12.1")
