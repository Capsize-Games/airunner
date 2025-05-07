"""
PyInstaller hook for torchao package to ensure source code is properly preserved for triton JIT.

This hook ensures that torchao's source code is properly collected, especially code that uses
triton's JIT compilation features in the kernel submodule.
"""

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)
import os

# Collect all submodules to ensure imports work properly
hiddenimports = collect_submodules("torchao")

# Add explicit hiddenimports for the kernel module that uses triton
hiddenimports += [
    "torchao.kernel",
    "torchao.kernel.bsr_triton_ops",
    "torchao.quantization",
]

# Collect torchao metadata
datas = copy_metadata("torchao")

# Collect all python files within torchao
# include_py_files=True ensures .py files are included (not just compiled .pyc)
datas += collect_data_files("torchao", include_py_files=True)


# Collect any additional data files that might be needed by torchao
def extra_torchao_files():
    """Find additional torchao files needed for source inspection."""
    import torchao

    torchao_path = os.path.dirname(torchao.__file__)
    result = []

    # Walk the torchao directory and add all .py files
    for root, _, files in os.walk(torchao_path):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(
                    full_path, os.path.dirname(torchao_path)
                )
                dest_dir = os.path.dirname(rel_path)
                result.append((full_path, dest_dir))

    return result


# Add the extra files only if we can import torchao
try:
    datas += extra_torchao_files()
except ImportError:
    pass
