"""
PyInstaller hook for diffusers package to ensure proper importing of loaders.

This hook ensures that diffusers' FromSingleFileMixin and other loader
mixins are properly collected and available at runtime.
"""

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)

# Collect all submodules of diffusers
hiddenimports = collect_submodules("diffusers")

# Add explicit imports for the problematic loaders modules
hiddenimports += [
    "diffusers.loaders",
    "diffusers.loaders.single_file",  # For FromSingleFileMixin
    "diffusers.loaders.ip_adapter",  # For IPAdapterMixin
    "diffusers.loaders.lora",  # For StableDiffusionLoraLoaderMixin
    "diffusers.loaders.textual_inversion",  # For TextualInversionLoaderMixin
]

# Collect metadata for diffusers
datas = copy_metadata("diffusers")

# Collect all data files (including .py files) from the diffusers package
datas += collect_data_files("diffusers", include_py_files=True)

# Also ensure safetensors is properly included as it's used by the loaders
hiddenimports += collect_submodules("safetensors")
datas += copy_metadata("safetensors")
datas += collect_data_files("safetensors", include_py_files=True)
