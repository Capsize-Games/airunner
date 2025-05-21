import builtins
import os
import unittest
from darklock.restrict_os_access import RestrictOSAccess


class TestRestrictOSAccess(unittest.TestCase):
    def setUp(self):
        self.restrict_os_access1 = RestrictOSAccess()
        self.restrict_os_access2 = RestrictOSAccess()

    def test_singleton(self):
        self.assertEqual(self.restrict_os_access1, self.restrict_os_access2)

    def test_activate(self):
        self.restrict_os_access1.activate()
        self.assertIsNotNone(self.restrict_os_access1.original_open)
        self.assertIsNotNone(self.restrict_os_access1.original_import)
        self.assertIsNotNone(self.restrict_os_access1.original_os_write)
        self.assertIsNotNone(self.restrict_os_access1.original_makedirs)

    def test_deactivate(self):
        self.restrict_os_access1.deactivate()
        self.assertEqual(self.restrict_os_access1.original_open, builtins.open)
        self.assertEqual(self.restrict_os_access1.original_import, builtins.__import__)
        self.assertEqual(self.restrict_os_access1.original_os_write, os.write)
        self.assertEqual(self.restrict_os_access1.original_makedirs, os.makedirs)

    def test_restricted_methods(self):
        with self.assertRaises(PermissionError):
            self.restrict_os_access1.restricted_open('test.txt', 'w')
        with self.assertRaises(PermissionError):
            self.restrict_os_access1.restricted_import('os')
        with self.assertRaises(PermissionError):
            self.restrict_os_access1.restricted_os()
        with self.assertRaises(PermissionError):
            self.restrict_os_access1.restricted_sys()
        with self.assertRaises(PermissionError):
            self.restrict_os_access1.restricted_socket()

if __name__ == '__main__':
    unittest.main()
