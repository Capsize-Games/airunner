"""
PyInstaller Runtime Hook for RTX 50xx GPU support
This hook runs at application startup before any other code
"""

import os
import sys
import importlib.util
from pathlib import Path

print("RTX 50xx CUDA compatibility runtime hook executing...", file=sys.stderr)


# Detect if this is a 50xx build based on marker file
def is_rtx50xx_build():
    # Check if our marker file exists
    base_dir = (
        Path(sys._MEIPASS)
        if hasattr(sys, "_MEIPASS")
        else Path(__file__).parent.parent.parent
    )
    marker_path = base_dir / "_internal" / "rtx50xx_build"
    if marker_path.exists():
        return True

    # Alternative detection: check environment
    if os.environ.get("RTX_50XX_SUPPORT") == "1":
        return True

    # Last resort: check GPU name via CUDA
    try:
        import torch

        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            if "RTX 50" in device_name:
                return True
    except:
        pass

    return False


def apply_pytorch_settings():
    # Apply PyTorch-specific settings for RTX 50xx GPUs
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:128"
    os.environ["TORCH_USE_CUDA_DSA"] = "1"  # Enable device-side assertions
    os.environ["TORCH_CUDNN_V8_API_ENABLED"] = "1"  # Enable cuDNN v8 API
    os.environ["RTX_50XX_SUPPORT"] = "1"

    # Tell PyTorch to precompile operations for sm_120 architecture
    os.environ["TORCH_CUDNN_FORCE_SM_VERSION"] = "120"

    # Print debug info to help with troubleshooting
    print("RTX 50xx GPU support enabled")


# Apply RTX 50xx specific settings if this is a 50xx build
if is_rtx50xx_build():
    print("Detected RTX 50xx build or GPU, applying compatibility settings...")
    apply_pytorch_settings()

    # Pre-import critical modules to enable patching
    try:
        import torch
        import torch.nn
        import torch.nn.functional

        # Log CUDA info
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            print(f"CUDA device: {device_name}")
            print(f"PyTorch CUDA available: {torch.cuda.is_available()}")
            print(f"PyTorch CUDA version: {torch.version.cuda}")
    except:
        print(
            "Could not preload PyTorch - compatibility patching may be incomplete"
        )
