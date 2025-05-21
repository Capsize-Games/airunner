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
        self.original_open = None
        self.original_import = None
        self.logging_importer = None
        self.original_os_write = None
        self.original_makedirs = None

        self.whitelisted_operations = []  # [('open', '/dev/null')]
        self.whitelisted_filenames = []
        self.whitelisted_imports = []
        self.blacklisted_filenames = []
        self.whitelisted_directories = []

        self.log_disc_writter = LogDiscWriter()

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
            or "write" in self.whitelisted_directories
            or self.check_stack_trace()
        ):
            return self.original_os_write(*args, **kwargs)
        self.log_disc_writter(filename=filename)

    def restricted_open(self, *args, **kwargs):
        if (
            self.is_directory_whitelisted(args[0])
            or "open" in self.whitelisted_operations
            or self.check_stack_trace()
        ):
            return self.original_open(*args, **kwargs)
        self.logger.error("File system operations are not allowed")

    def restricted_os_makedirs(self, *args, **kwargs):
        if (
            self.is_directory_whitelisted(args[0])
            or "makedirs" in self.whitelisted_operations
            or self.check_stack_trace()
        ):
            return self.original_makedirs(*args, **kwargs)
        self.logger.error(
            f"File system operations are not allowed. Attempted to create directory: {args}"
        )

    def restricted_exec(self, *args, **kwargs):
        if (
            self.is_directory_whitelisted(args[0])
            or "exec" in self.whitelisted_operations
            or self.check_stack_trace()
        ):
            return os.exec(*args, **kwargs)
        self.logger.error("System calls are not allowed")

    def restricted_subprocess(self, *args, **kwargs):
        if (
            self.is_directory_whitelisted(args[0])
            or "subprocess" in self.whitelisted_operations
            or self.check_stack_trace()
        ):
            return os.system(*args, **kwargs)
        self.logger.error("Subprocess invocations are not allowed")

    def restricted_import(self, name, *args, **kwargs):
        if "import" in self.whitelisted_operations or self.check_stack_trace():
            return self.original_import(name, *args, **kwargs)
        if any(
            re.search(pattern, name) for pattern in self.whitelisted_imports
        ):
            return self.original_import(name, *args, **kwargs)
        print(f"Failed to import: {name}")
        self.logger.error("Importing modules is not allowed")

    def log_imports(self, name, *args, **kwargs):
        # self.logging_importer = LoggingImporter()
        sys.meta_path.insert(0, self.logging_importer)

    def restricted_module(self, *args, **kwargs):
        self.logger.error("Module operations are not allowed")

    def restricted_os(self, *args, **kwargs):
        self.logger.error("OS operations are not allowed")

    def restricted_sys(self, *args, **kwargs):
        self.logger.error("System operations are not allowed")

    def restricted_socket(self, *args, **kwargs):
        self.logger.error("Socket operations are not allowed")

    def check_stack_trace(self) -> bool:
        stack_trace = traceback.extract_stack()
        # Add more logic here to check the stack trace
        # and allow certain operations
        # from specific chains.
        res = False
        for frame in stack_trace:
            for name in self.whitelisted_filenames:
                if name in frame.filename:
                    res = True
            for name in self.blacklisted_filenames:
                if name in frame.filename:
                    res = False
        return res

    def log_writes(self):
        os.write = LogDiscWriter()

    def activate(
        self,
        whitelisted_operations: list = None,
        whitelisted_filenames: list = None,
        whitelisted_imports: list = None,
        blacklisted_filenames: list = None,
        whitelisted_directories: list = None,
    ):
        """
        Install restrictions on OS access.
        :return:
        """
        self.whitelisted_operations = whitelisted_operations or []
        self.whitelisted_filenames = whitelisted_filenames or []
        self.whitelisted_imports = whitelisted_imports or []
        self.blacklisted_filenames = blacklisted_filenames or []

        whitelisted_directories = whitelisted_directories or []
        parsed_directories = []
        for directory in whitelisted_directories:
            parsed_directories.append(os.path.expanduser(directory))
        self.whitelisted_directories = parsed_directories

        self.original_open = builtins.open
        self.original_import = builtins.__import__
        self.original_os_write = os.write
        self.original_makedirs = os.makedirs

        os.makedirs = self.restricted_os_makedirs

        os.write = self.restrict_os_write

        # builtins.open = self.restricted_open

        # self.log_writes()

    def deactivate(self):
        """
        Uninstall the restrictions on OS access.
        :return:
        """
        builtins.open = self.original_open
        os.system = os.system
        os.popen = os.popen
        if "subprocess" in sys.modules:
            sys.modules["subprocess"].Popen = sys.modules["subprocess"].Popen
        builtins.__import__ = self.original_import
        os.write = (
            self.original_os_write
        )  # restore os.write to its original state
        os.makedirs = (
            self.original_makedirs
        )  # restore os.makedirs to its original state
