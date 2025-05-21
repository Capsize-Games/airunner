from airunner.facehuggershield.darklock.singleton import Singleton
from airunner.facehuggershield.darklock.log_disc_writer import LogDiscWriter
import builtins
import re
import os
import sys
import traceback
import logging


class RestrictOSAccess(metaclass=Singleton):
    def __init__(self):
        self.original_open = builtins.open  # Store original at init
        self.original_import = builtins.__import__  # Store original at init
        self.original_os_write = os.write  # Store original at init
        self.original_makedirs = os.makedirs  # Store original at init
        self.logging_importer = None

        self.whitelisted_operations = []  # [('open', '/dev/null')]
        self.whitelisted_filenames = []
        self.whitelisted_imports = []
        self.blacklisted_filenames = []
        self.whitelisted_directories = []

        # Internal core modules that should always be allowed for the class to function
        self.core_internal_imports = [
            "traceback",
            "linecache",
            "io",
            "re",
            "logging",
            "collections.abc",
            "os",
            "sys",
            "tokenize",
            "ast",
        ]

        self.log_disc_writer = LogDiscWriter()

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.StreamHandler())

    def is_directory_whitelisted(self, directory: str) -> bool:
        for d in self.whitelisted_directories:
            if str(d) in str(directory):
                return True
        return False

    def restrict_os_write(self, *args, **kwargs):
        stack = traceback.extract_stack()
        filename = stack[-2].filename
        if (
            self.is_directory_whitelisted(args[0])
            or "write"
            in self.whitelisted_operations  # Corrected: was self.whitelisted_directories
            or self.check_stack_trace()
        ):
            return self.original_os_write(*args, **kwargs)
        self.log_disc_writter(filename=filename)
        self.logger.error(
            "OS write operations are not allowed"
        )  # Added logger
        raise PermissionError("OS write operations are not allowed")

    def restricted_open(self, *args, **kwargs):
        # Check if args is not empty and args[0] is a string before using it
        file_path_arg = args[0] if args and isinstance(args[0], str) else ""

        if (
            (file_path_arg and self.is_directory_whitelisted(file_path_arg))
            or "open" in self.whitelisted_operations
            or self.check_stack_trace()
        ):
            return self.original_open(*args, **kwargs)
        self.logger.error(
            f"File system open operations are not allowed. Attempted: open({args}, {kwargs})"
        )
        raise PermissionError("File system open operations are not allowed")

    def restricted_os_makedirs(self, *args, **kwargs):
        # Check if args is not empty and args[0] is a string before using it
        dir_path_arg = args[0] if args and isinstance(args[0], str) else ""
        if (
            (dir_path_arg and self.is_directory_whitelisted(dir_path_arg))
            or "makedirs" in self.whitelisted_operations
            or self.check_stack_trace()
        ):
            return self.original_makedirs(*args, **kwargs)
        self.logger.error(
            f"File system makedirs operations are not allowed. Attempted to create directory: {args}"
        )
        raise PermissionError(
            "File system makedirs operations are not allowed"
        )

    def restricted_exec(self, *args, **kwargs):
        # Check if args is not empty and args[0] is a string before using it
        path_arg = args[0] if args and isinstance(args[0], str) else ""
        if (
            (path_arg and self.is_directory_whitelisted(path_arg))
            or "exec" in self.whitelisted_operations
            or self.check_stack_trace()
        ):
            # Ensure os.execv, os.execl, etc. are called correctly
            # This part might need more specific handling depending on which os.exec* function is intended
            if hasattr(os, args[0]) and callable(
                getattr(os, args[0])
            ):  # A basic check
                return getattr(os, args[0])(
                    *(args[1:]), **kwargs
                )  # Call the original os.exec*
            else:  # Fallback or error
                self.logger.error(
                    f"Attempted to call an unsupported exec function: {args[0]}"
                )
                raise PermissionError(
                    "System calls via os.exec* are not allowed or misconfigured"
                )

        self.logger.error(
            f"System calls via os.exec* are not allowed. Attempted: {args}"
        )
        raise PermissionError("System calls via os.exec* are not allowed")

    def restricted_subprocess(self, *args, **kwargs):
        # This method seems to intend to restrict os.system, not general subprocess module
        # For os.system, the first argument is the command string.
        cmd_arg = args[0] if args and isinstance(args[0], str) else ""

        if (
            # is_directory_whitelisted might not be relevant for os.system commands unless they specify paths
            # Consider a more specific check if needed, e.g., based on command patterns
            "subprocess" in self.whitelisted_operations  # or "os.system"
            or self.check_stack_trace()
        ):
            return os.system(*args, **kwargs)  # Call original os.system
        self.logger.error(
            f"Subprocess invocations via os.system are not allowed. Attempted: {args}"
        )
        raise PermissionError(
            "Subprocess invocations via os.system are not allowed"
        )

    def restricted_import(self, name, *args, **kwargs):
        # Allow core internal imports unconditionally
        if name in self.core_internal_imports:
            return self.original_import(name, *args, **kwargs)

        if "import" in self.whitelisted_operations or self.check_stack_trace():
            return self.original_import(name, *args, **kwargs)
        if any(
            re.search(pattern, name) for pattern in self.whitelisted_imports
        ):
            return self.original_import(name, *args, **kwargs)
        # print(f"Failed to import: {name}") # This print might be too noisy
        self.logger.error(f"Importing module '{name}' is not allowed")
        raise PermissionError(f"Importing module '{name}' is not allowed")

    def log_imports(self, name, *args, **kwargs):
        # self.logging_importer = LoggingImporter()
        # Ensure LoggingImporter is defined or imported if this is to be used
        if self.logging_importer:
            sys.meta_path.insert(0, self.logging_importer)
        else:
            self.logger.warning(
                "LoggingImporter not set, cannot log imports via meta_path."
            )

    def restricted_module(
        self, *args, **kwargs
    ):  # This method is generic, what module ops does it restrict?
        self.logger.error("Module operations are not allowed")
        raise PermissionError("Module operations are not allowed")

    def activate(self):
        self.logger.info("Activating OS restrictions")
        # Store originals if not already stored (e.g. if activate is called multiple times)
        if (
            builtins.open == self.restricted_open
            and builtins.__import__ == self.restricted_import
            and os.write == self.restrict_os_write
            and os.makedirs == self.restricted_os_makedirs
        ):
            self.logger.warning(
                "OS restrictions seem to be already active or originals not properly restored previously."
            )
            # Potentially restore them first before re-patching, or just log and proceed
            # For now, we assume deactivate will be called correctly.

        # Patch builtins and os module
        builtins.open = self.restricted_open
        builtins.__import__ = self.restricted_import
        os.write = self.restrict_os_write
        os.makedirs = self.restricted_os_makedirs
        # Add other restrictions as needed, e.g., for os.system, os.exec*
        # For example:
        # self.original_os_system = os.system
        # os.system = self.restricted_subprocess
        # self.original_os_execv = os.execv # and other exec variants
        # os.execv = self.restricted_exec # (restricted_exec needs to handle different exec signatures)

    def deactivate(self):
        self.logger.info("Deactivating OS restrictions")
        builtins.open = self.original_open
        builtins.__import__ = self.original_import
        os.write = self.original_os_write
        os.makedirs = self.original_makedirs
        # Restore other patched os functions if any
        # if hasattr(self, 'original_os_system'):
        #     os.system = self.original_os_system
        # if hasattr(self, 'original_os_execv'):
        #     os.execv = self.original_os_execv

    def check_stack_trace(self, allowed_callers=None):
        """
        Checks the stack trace for allowed callers.
        This is a placeholder and needs a robust implementation if used for security.
        """
        # Example: Allow if called from a specific module or function
        # For demonstration, always returns False unless implemented
        # stack = traceback.extract_stack()
        # for frame in stack:
        #     if allowed_callers and frame.name in allowed_callers:
        #          return True
        return False  # Default to not allowing by stack trace check

    # Whitelisting methods
    def add_whitelisted_operation(
        self, operation_type: str, value: str = None
    ):
        if value:
            self.whitelisted_operations.append((operation_type, value))
        else:
            self.whitelisted_operations.append(operation_type)
        self.logger.info(
            f"Added to whitelist: operation_type='{operation_type}', value='{value}'"
        )

    def add_whitelisted_filename(self, filename: str):
        self.whitelisted_filenames.append(filename)
        self.logger.info(f"Added filename to whitelist: {filename}")

    def add_whitelisted_import(
        self, import_name: str
    ):  # Can be a regex pattern
        self.whitelisted_imports.append(import_name)
        self.logger.info(f"Added import to whitelist: {import_name}")

    def add_whitelisted_directory(self, directory: str):
        abs_dir = os.path.abspath(directory)
        if abs_dir not in self.whitelisted_directories:
            self.whitelisted_directories.append(abs_dir)
            self.logger.info(f"Added directory to whitelist: {abs_dir}")

    def clear_whitelists(self):
        self.whitelisted_operations = []
        self.whitelisted_filenames = []
        self.whitelisted_imports = []
        self.whitelisted_directories = []
        self.logger.info("Cleared all whitelists.")


# Example of a LoggingImporter (conceptual)
# class LoggingImporter:
#     def find_module(self, fullname, path=None):
#         logging.info(f"Import attempt: {fullname}")
#         return None # Let the default mechanism handle the import
