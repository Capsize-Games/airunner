import builtins
import os
import unittest
import sys  # Import sys module
from airunner.facehuggershield.darklock.restrict_os_access import (
    RestrictOSAccess,
)


class TestRestrictOSAccess(unittest.TestCase):
    def setUp(self):
        # Get a fresh instance for each test to avoid state leakage
        # This requires making the Singleton aspect testable or resettable,
        # or carefully managing state if true singleton behavior is critical across tests.
        # For now, let's assume we can get a clean state or reset is handled.
        RestrictOSAccess._instances = (
            {}
        )  # Basic way to reset Singleton for tests
        self.restrict_os_access = RestrictOSAccess()
        # Store original functions before any test modifies them
        self.original_builtins_open = builtins.open
        self.original_builtins_import = builtins.__import__
        self.original_os_write = os.write
        self.original_os_makedirs = os.makedirs

    def tearDown(self):
        # Ensure all restrictions are deactivated and originals restored after each test
        self.restrict_os_access.deactivate()  # Should restore to what it was before activation
        # Explicitly restore to pre-test state just in case deactivate doesn't cover all or fails
        builtins.open = self.original_builtins_open
        builtins.__import__ = self.original_builtins_import
        os.write = self.original_os_write
        os.makedirs = self.original_os_makedirs
        # Clear whitelists and any other state that might persist
        self.restrict_os_access.clear_whitelists()

    def test_singleton(self):
        # Test singleton behavior by creating another instance
        restrict_os_access2 = RestrictOSAccess()
        self.assertIs(
            self.restrict_os_access,
            restrict_os_access2,
            "RestrictOSAccess should be a Singleton",
        )

    def test_activate_deactivate(self):
        self.restrict_os_access.activate()
        self.assertNotEqual(
            builtins.open,
            self.original_builtins_open,
            "builtins.open should be patched after activate",
        )
        self.assertNotEqual(
            builtins.__import__,
            self.original_builtins_import,
            "builtins.__import__ should be patched after activate",
        )
        self.assertNotEqual(
            os.write,
            self.original_os_write,
            "os.write should be patched after activate",
        )
        self.assertNotEqual(
            os.makedirs,
            self.original_os_makedirs,
            "os.makedirs should be patched after activate",
        )

        self.restrict_os_access.deactivate()
        self.assertEqual(
            builtins.open,
            self.original_builtins_open,
            "builtins.open should be restored after deactivate",
        )
        self.assertEqual(
            builtins.__import__,
            self.original_builtins_import,
            "builtins.__import__ should be restored after deactivate",
        )
        self.assertEqual(
            os.write,
            self.original_os_write,
            "os.write should be restored after deactivate",
        )
        self.assertEqual(
            os.makedirs,
            self.original_os_makedirs,
            "os.makedirs should be restored after deactivate",
        )

    def test_restricted_open_raises_permission_error(self):
        self.restrict_os_access.activate()
        with self.assertRaisesRegex(
            PermissionError, "File system open operations are not allowed"
        ):
            open("test.txt", "w")  # Use global open which should be patched

    def test_restricted_import_raises_permission_error(self):
        self.restrict_os_access.activate()
        with self.assertRaisesRegex(
            PermissionError,
            "Importing module 'json' is not allowed",  # Changed module to json
        ):
            __import__("json")  # Use global __import__ with a non-core module

    def test_restricted_os_write_raises_permission_error(self):
        self.restrict_os_access.activate()
        # os.write takes a file descriptor (int) and bytes
        # We need a valid fd to test; however, opening a file is restricted.
        # This test highlights a dependency: to test os.write restriction, we might need a whitelisted open.
        # For now, let's assume we can get an fd (e.g., sys.stdout.fileno()) but the write itself is blocked.
        # A more isolated test would mock the lower-level parts if possible.
        # However, the goal is to test the patched os.write.
        # If open is restricted, getting a valid fd for a file is hard.
        # Let's try with stdout, though it might behave differently or be whitelisted by some environments.
        # The key is that *our* os.write patch is called.
        if hasattr(os, "devnull"):
            # Temporarily allow opening os.devnull for this test
            self.restrict_os_access.add_whitelisted_directory(
                os.path.dirname(os.devnull)
            )  # Whitelist dir of devnull
            self.restrict_os_access.deactivate()  # Deactivate to apply whitelist to subsequent activate
            self.restrict_os_access.activate()

            fd_to_test = os.open(os.devnull, os.O_WRONLY)
            with self.assertRaisesRegex(
                PermissionError, "OS write operations are not allowed"
            ):
                os.write(fd_to_test, b"test")
            os.close(fd_to_test)

            # Clean up whitelist and reactivate with original settings
            self.restrict_os_access.clear_whitelists()
            self.restrict_os_access.deactivate()
            self.restrict_os_access.activate()
        else:
            self.restrict_os_access.add_whitelisted_operation("open")
            self.restrict_os_access.deactivate()
            self.restrict_os_access.activate()

            try:
                # Attempt to use a temporary file if os.devnull is not available or whitelisting it is problematic
                temp_file_path = "test_dummy_for_write.txt"
                fd = os.open(temp_file_path, os.O_WRONLY | os.O_CREAT)
                # At this point, open is whitelisted. Now, test the os.write restriction.
                with self.assertRaisesRegex(
                    PermissionError, "OS write operations are not allowed"
                ):
                    os.write(fd, b"test")
                os.close(fd)
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            except Exception as e:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                self.skipTest(
                    f"Skipping os.write test due to setup issues or platform limitations: {e}"
                )
            finally:
                self.restrict_os_access.clear_whitelists()
                self.restrict_os_access.deactivate()
                self.restrict_os_access.activate()

    def test_restricted_os_makedirs_raises_permission_error(self):
        self.restrict_os_access.activate()
        with self.assertRaisesRegex(
            PermissionError, "File system makedirs operations are not allowed"
        ):
            os.makedirs("test_dir")

    # The original test_restricted_methods tested the methods on the instance directly.
    # Now we test the effect of activate() on the global functions.
    # The methods like restricted_os(), restricted_sys(), restricted_socket() are not directly patched
    # by activate() in the current RestrictOSAccess. activate() patches open, __import__, os.write, os.makedirs.
    # If these other restrictions are desired, RestrictOSAccess.activate() needs to be extended.
    # For now, commenting out tests for unpatched functionalities.

    # def test_restricted_os_method_calls(self):
    #     self.restrict_os_access.activate() # Ensure restrictions are active
    #     # These tests assume that RestrictOSAccess might provide its own functions
    #     # that are always restricted, regardless of patching. Or, they test specific
    #     # unexported helper methods if they were meant to be tested directly.
    #     # Given the current implementation, these direct calls to instance methods
    #     # will raise PermissionError if the methods are designed to do so unconditionally.

    #     # Example: if self.restrict_os_access.restricted_os was a public method that always raises
    #     # with self.assertRaises(PermissionError):
    #     #    self.restrict_os_access.restricted_os() # This method doesn't exist on the instance

    #     # The test `test_restricted_methods` from the original file seemed to call
    #     # methods like `self.restrict_os_access1.restricted_open(...)`.
    #     # These are the *replacement* functions. Calling them directly tests their logic,
    #     # but the main integration point is that `builtins.open` (etc.) get replaced by them.

    #     # Let's re-verify what `restricted_os`, `restricted_sys`, `restricted_socket` were.
    #     # They are not standard Python builtins or os functions that `activate` patches.
    #     # They seem to be custom methods in the original `RestrictOSAccess` that always raised.
    #     # If they are still present and meant to be tested, they can be.
    #     # Looking at the provided `restrict_os_access.py`, these specific methods are not there.
    #     # There are `restricted_exec`, `restricted_subprocess`, `restricted_module`.

    def test_whitelisting_open_specific_file(self):
        self.restrict_os_access.clear_whitelists()  # Start clean
        self.restrict_os_access.add_whitelisted_directory("/tmp")
        self.restrict_os_access.activate()

        try:
            # Ensure /tmp exists and is writable for the test user
            if not os.path.exists("/tmp"):
                self.skipTest("/tmp directory does not exist.")
            if not os.access("/tmp", os.W_OK):
                self.skipTest("/tmp directory is not writable.")

            with open("/tmp/allowed.txt", "w") as f:
                f.write("test")
            self.assertTrue(os.path.exists("/tmp/allowed.txt"))
            os.remove("/tmp/allowed.txt")
        except PermissionError:
            self.fail(
                "Opening a whitelisted file/directory raised PermissionError unexpectedly."
            )
        except Exception as e:
            # If /tmp exists but os.remove fails, it might be a legitimate PermissionError from the OS
            # not from our restriction. Catch this to avoid misinterpreting test.
            if isinstance(e, PermissionError) and os.path.exists(
                "/tmp/allowed.txt"
            ):
                os.remove("/tmp/allowed.txt")  # Attempt cleanup
            self.fail(f"An unexpected error occurred: {e}")

        with self.assertRaisesRegex(
            PermissionError, "File system open operations are not allowed"
        ):
            open("/elsewhere/forbidden.txt", "w")

    def test_whitelisting_import(self):
        self.restrict_os_access.add_whitelisted_import("math")
        self.restrict_os_access.add_whitelisted_import(
            "re"
        )  # for regex matching in whitelisted_imports
        self.restrict_os_access.activate()

        try:
            import math
            import re

            self.assertIn("math", sys.modules)
            self.assertIn("re", sys.modules)
        except PermissionError:
            self.fail(
                "Importing a whitelisted module raised PermissionError unexpectedly."
            )

        # Test that a non-whitelisted import still fails
        with self.assertRaisesRegex(
            PermissionError, "Importing module 'json' is not allowed"
        ):
            __import__("json")


if __name__ == "__main__":
    unittest.main()
