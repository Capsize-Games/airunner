import builtins
import re
import os
import sys
import traceback
import importlib.abc
import importlib.util


# class LoggingImporter(importlib.abc.MetaPathFinder):
#     def __init__(self):
#         self.imported_files = {}
#
#     def find_spec(self, fullname, path, target=None):
#         top_level_module = fullname.split('.')[0]
#
#         # Get the current stack frames
#         current_frames = traceback.extract_stack(limit=10)
#         # Iterate over the frames backwards
#         for frame in reversed(current_frames):
#             # Extract the filename of the file that is importing the module
#             importing_file = frame.filename
#             # If the file is not part of the import system, use it
#             if "<frozen " not in importing_file:
#                 break
#
#
#         if not fullname.endswith("_ui"):
#             if importing_file not in self.imported_files:
#                 self.imported_files[importing_file] = {}
#             if top_level_module not in self.imported_files[importing_file]:
#                 self.imported_files[importing_file][top_level_module] = set()
#
#             self.imported_files[importing_file][top_level_module].add(fullname)
#         return None  # Let the next finder in the chain handle the actual import


class LogDiscWriter:
    """
    Logs all writing attempts to the disk

    """

    def __init__(self):
        self.total_write_attempts = 0

    def __call__(self, *args, **kwargs):
        self.total_write_attempts += 1
        print(f"Write attempt: {self.total_write_attempts}")

        # show where write came from:
        stack = traceback.extract_stack()
        print(f"Write attempt from: {stack[-2]}")



class RestrictOSAccess:
    def __init__(self):
        self.original_open = None
        self.original_import = None
        self.logging_importer = None
        self.original_os_write = None
        self.original_makedirs = None

        self.whitelisted_operations = []#[('open', '/dev/null')]
        self.whitelisted_filenames = [
        ]
        self.whitelisted_imports = [
        ]
        self.blacklisted_filenames = [
        ]
        self.os_write_blacklisted_modules = [
            "huggingface_hub",
            "transformers",
            "diffusers",
        ]

    def restrict_os_write(self, *args, **kwargs):
        return self.original_os_write(*args, **kwargs)

    def restricted_os_makedirs(self, *args, **kwargs):
        if ('makedirs', args[0]) in self.whitelisted_operations or self.check_stack_trace():
            return self.original_makedirs(*args, **kwargs)
        raise PermissionError("File system operations are not allowed")

    def restricted_open(self, *args, **kwargs):
        if ('open', args[0]) in self.whitelisted_operations or self.check_stack_trace():
            return self.original_open(*args, **kwargs)
        raise PermissionError("File system operations are not allowed")

    def restricted_exec(self, *args, **kwargs):
        raise PermissionError("System calls are not allowed")

    def restricted_subprocess(self, *args, **kwargs):
        raise PermissionError("Subprocess invocations are not allowed")

    def restricted_import(self, name, *args, **kwargs):
        if any(re.search(pattern, name) for pattern in self.whitelisted_imports):
            return self.original_import(name, *args, **kwargs)
        print(f"Failed to import: {name}")
        raise PermissionError("Importing modules is not allowed")

    def log_imports(self, name, *args, **kwargs):
        #self.logging_importer = LoggingImporter()
        sys.meta_path.insert(0, self.logging_importer)

    def restricted_module(self, *args, **kwargs):
        raise PermissionError("Module operations are not allowed")

    def restricted_os(self, *args, **kwargs):
        raise PermissionError("OS operations are not allowed")

    def restricted_sys(self, *args, **kwargs):
        raise PermissionError("System operations are not allowed")

    def restricted_socket(self, *args, **kwargs):
        raise PermissionError("Socket operations are not allowed")

    def check_stack_trace(self):
        stack_trace = traceback.extract_stack()
        # Add your logic here to check the stack trace and allow certain operations
        # from specific chains. For example:
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

    def install(self):
        # Save original functions
        pass
        self.original_open = builtins.open
        self.original_import = builtins.__import__
        self.original_os_write = os.write
        self.original_makedirs = os.makedirs

        # Override built-in open function
        # builtins.open = self.restricted_open
        os.makedirs = self.restricted_os_makedirs

        # Override os.system and os.popen
        # os.system = self.restricted_exec
        # os.popen = self.restricted_exec
        os.write = self.restrict_os_write

        # Override subprocess
        # if 'subprocess' in sys.modules:
        #     sys.modules['subprocess'].Popen = self.restricted_subprocess

        # Override import
        # builtins.__import__ = self.restricted_import
        #self.log_imports("test")
        self.log_writes()

        # # Override module
        # builtins.module = self.restricted_module
        #
        # # Override os
        # builtins.os = self.restricted_os
        #
        # # Override sys
        # builtins.sys = self.restricted_sys
        #
        # # Override socket
        # builtins.socket = self.restricted_socket

    def uninstall(self):
        # Restore original functions
        builtins.open = self.original_open
        os.system = os.system
        os.popen = os.popen
        if 'subprocess' in sys.modules:
            sys.modules['subprocess'].Popen = sys.modules['subprocess'].Popen
        builtins.__import__ = builtins.__import__
        builtins.module = builtins.module
        builtins.os = builtins.os
        builtins.sys = builtins.sys
        builtins.socket = builtins.socket
