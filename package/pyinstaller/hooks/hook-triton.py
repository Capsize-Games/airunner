"""
PyInstaller hook for triton package to ensure source code is preserved for inspection.

This hook ensures that triton's source code is properly collected for use by inspect.getsourcelines()
which is needed for triton's JIT compilation process.
"""

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)
import os
import sys

# Collect all submodules to ensure imports work properly
hiddenimports = collect_submodules("triton")

# Collect triton metadata
datas = copy_metadata("triton")

# Collect all python files within triton
# include_py_files=True ensures .py files are included (not just compiled .pyc)
datas += collect_data_files("triton", include_py_files=True)


# Collect any additional data files that might be needed by triton
# This is especially important for source files used by inspect.getsourcelines()
def extra_triton_files():
    """Find additional triton files needed for source inspection."""
    import triton

    triton_path = os.path.dirname(triton.__file__)
    result = []

    # Walk the triton directory and add all .py files
    for root, _, files in os.walk(triton_path):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(
                    full_path, os.path.dirname(triton_path)
                )
                dest_dir = os.path.dirname(rel_path)
                result.append((full_path, dest_dir))

    return result


# Add the extra files only if we can import triton
try:
    datas += extra_triton_files()
except ImportError:
    pass
