"""
PyInstaller runtime hook to set CUDA-related environment variables.

This hook runs when the packaged application starts and sets environment
variables to help with CUDA compatibility and debugging.
"""

import os
import sys

# Set CUDA environment variables for better error reporting and compatibility
os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"
os.environ["CUDA_MODULE_LOADING"] = "LAZY"

# Log CUDA environment info for debugging
print("CUDA runtime hook executed", file=sys.stderr)
print(f"CUDA_HOME: {os.environ.get('CUDA_HOME', 'Not set')}", file=sys.stderr)
print(
    f"LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH', 'Not set')}",
    file=sys.stderr,
)

# Try to diagnose CUDA capabilities
try:
    import torch

    print(
        f"PyTorch CUDA available: {torch.cuda.is_available()}", file=sys.stderr
    )
    if torch.cuda.is_available():
        print(
            f"CUDA device count: {torch.cuda.device_count()}", file=sys.stderr
        )
        print(
            f"Current CUDA device: {torch.cuda.current_device()}",
            file=sys.stderr,
        )
        print(
            f"CUDA device name: {torch.cuda.get_device_name(0)}",
            file=sys.stderr,
        )
        print(f"PyTorch CUDA version: {torch.version.cuda}", file=sys.stderr)
except ImportError:
    print("Could not import torch for CUDA diagnostics", file=sys.stderr)
except Exception as e:
    print(f"Error checking CUDA info: {e}", file=sys.stderr)
