# NVIDIA TensorRT Setup on Windows 11 for airunner

This guide details the steps to set up NVIDIA TensorRT for use with the airunner project on a Windows 11 system. The primary method focuses on using the TensorRT Python package, which bundles the necessary runtime libraries.

## Prerequisites

1.  **NVIDIA GPU:** A compatible NVIDIA GPU is required. Refer to the [NVIDIA CUDA GPUs - Support Matrix](https://developer.nvidia.com/cuda-gpus) for a list of supported GPUs.
2.  **NVIDIA Graphics Driver:** Install the latest NVIDIA Studio Driver or Game Ready Driver for your GPU from the [NVIDIA Driver Downloads page](https://www.nvidia.com/Download/index.aspx).
3.  **CUDA Toolkit:**
    *   TensorRT 10.x is typically compatible with CUDA 12.x. The airunner project aims for CUDA 12.x compatibility.
    *   Download and install the [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads) (e.g., version 12.4 or as specified by the TensorRT version you intend to use).
    *   During installation, it's recommended to choose the "Express" installation. If choosing "Custom," ensure the driver components are not downgraded if you have a newer driver installed.
    *   The CUDA Toolkit installation will typically set the `CUDA_PATH` environment variable (e.g., `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4`).

## Method 1: Python Package Installation (Recommended for Python-only use)

The TensorRT Python package (`tensorrt`) available via PyPI includes the necessary runtime libraries. This is the recommended method if you are primarily using TensorRT through its Python API within airunner.

1.  **Ensure Python and Pip are Installed:**
    *   Python 3.8 to 3.13 is supported by recent TensorRT Python packages. Ensure your Python version is compatible.
    *   Make sure pip is up-to-date:
        ```bash
        python -m pip install --upgrade pip wheel setuptools
        ```

2.  **Install TensorRT Python Package:**
    *   Install the `tensorrt` package. For compatibility with CUDA 12.x, it's best to specify the CUDA version in the package name if available (e.g., `tensorrt-cu12`). If the exact version `10.9.0.34` is not available with a specific CUDA suffix, pip should resolve to a compatible build.
        ```bash
        # Replace 10.9.0.34 with the specific version if needed and available
        # The -cu12 suffix might be part of the main package or a separate meta-package
        # depending on NVIDIA's current PyPI strategy.
        # Start with the base, pip might resolve CUDA specific wheels.
        python -m pip install tensorrt==10.9.0.34
        ```
    *   If the above doesn't automatically pick a CUDA 12.x compatible version, or if you encounter issues, you might need to find the exact wheel name or use a command like:
        ```bash
        # Example for TensorRT 10.x targeting CUDA 12.x.
        # The exact package name might vary (e.g. tensorrt[cu12x] or similar)
        # Refer to NVIDIA's official Python package installation instructions if a plain version install fails.
        python -m pip install tensorrt-cu12 # Or tensorrt[cu12] etc.
        ```
        NVIDIA's documentation indicates that `python3 -m pip install --upgrade tensorrt` defaults to CUDA 12.x variants.

3.  **Verification:**
    Run the following Python commands to verify the installation:
    ```python
    import tensorrt
    print(f"TensorRT version: {tensorrt.__version__}")
    logger = tensorrt.Logger()
    builder = tensorrt.Builder(logger)
    if builder:
        print("TensorRT Builder created successfully.")
    else:
        print("Error: Could not create TensorRT Builder.")
    # For CUDA checks (if builder creation is not enough)
    # Note: TensorRT itself being usable is the primary check.
    # Direct CUDA checks via PyTorch (if installed) can also be informative:
    # import torch
    # print(f"PyTorch CUDA available: {torch.cuda.is_available()}")
    # if torch.cuda.is_available():
    #     print(f"PyTorch CUDA version: {torch.version.cuda}")
    ```
    If the `tensorrt.Builder` object can be created, it indicates that TensorRT has found a compatible CUDA environment.

## Method 2: Zip File Installation (SDK for C++ Development or Advanced Users)

This method involves downloading the TensorRT SDK. It's generally needed if you plan to compile C++ TensorRT applications, custom plugins, or if the Python package method encounters issues.

1.  **Download TensorRT SDK:**
    *   Go to the [NVIDIA TensorRT Download Page](https://developer.nvidia.com/tensorrt) (requires NVIDIA Developer Program membership).
    *   Download the TensorRT 10.x (e.g., 10.1.0 or a version close to `10.9.0.34` if that specific patch isn't available as an SDK download) ZIP package for Windows and your corresponding CUDA version (e.g., CUDA 12.x).

2.  **Extract SDK:**
    *   Choose an installation location (e.g., `C:\NVIDIA\TensorRT-10.x.x.x`). This path will be referred to as `<installpath>`.
    *   Unzip the downloaded file to this location.

3.  **Configure Environment Variables:**
    *   Add the TensorRT library directory to your system's `PATH` environment variable:
        *   Press the Windows key, search for "environment variables," and select "Edit the system environment variables."
        *   Click "Environment Variables..."
        *   Under "System variables," find and select the `Path` variable, then click "Edit..."
        *   Click "New" and add the path to your TensorRT lib directory: `<installpath>\lib` (e.g., `C:\NVIDIA\TensorRT-10.x.x.x\lib`).
        *   Click "OK" on all dialogs to save the changes.
    *   Alternatively, you can copy the DLL files from `<installpath>\lib` to your CUDA installation's `bin` directory (e.g., `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x\bin`).

4.  **Install Python Wheel (if not using Method 1):**
    *   The ZIP package contains Python wheel files in the `<installpath>\python` directory.
    *   Install the appropriate wheel for your Python version (e.g., `cp310` for Python 3.10):
        ```bash
        cd <installpath>\python
        python -m pip install tensorrt-*-cp3x-none-win_amd64.whl
        ```
        (Replace `*-cp3x-` with the specific filename matching your Python version).

## Application Code Impact

*   If the airunner project uses TensorRT through its Python API, and the `tensorrt` Python package is used for installation, **no significant application code changes should be necessary for Windows compatibility.** The Python package is designed to abstract away OS-specific details.
*   Ensure that any code loading TensorRT models or engines uses paths compatible with Windows (e.g., using `pathlib` or correctly formatted string paths).

## Troubleshooting

*   **CUDA Initialization Failure:** If you see errors like `CUDA initialization failure`, ensure your NVIDIA drivers and CUDA Toolkit are correctly installed and compatible with the TensorRT version.
*   **DLL Not Found:** If `tensorrt` Python module imports but fails to load underlying libraries, double-check that the TensorRT `lib` directory (if using SDK method) or CUDA `bin` directory is correctly added to your system `PATH` and that a system restart (if required for PATH changes to take effect) has been performed. The pip package (Method 1) should avoid this by bundling libraries.
*   **Version Mismatches:** Ensure compatibility between the NVIDIA driver, CUDA Toolkit version, and TensorRT version. Refer to the [TensorRT Support Matrix](https://docs.nvidia.com/deeplearning/tensorrt/support-matrix/index.html) for official compatibility information.

This document provides guidance for setting up TensorRT on Windows. For airunner, relying on the Python package (Method 1) is the preferred and simpler approach.
