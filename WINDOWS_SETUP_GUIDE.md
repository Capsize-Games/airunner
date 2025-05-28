# Windows 11 Development Environment Setup for airunner

This guide details the steps to set up a Python development environment on Windows 11 for the airunner project.

## 1. Install Python

*   **Download Python:** Go to the official Python website (python.org) and download the installer for Python 3.13.3 (or the latest stable 3.11+ version if 3.13.3 is unavailable or causes issues).
*   **Run Installer:**
    *   Ensure you check the box that says **"Add Python to PATH"** during installation. This is crucial for running Python and pip from the command line.
    *   Choose the "Customize installation" option if you want to change the installation location or select optional features. Otherwise, the default installation is usually fine.
*   **Verify Installation:**
    Open a new Command Prompt (cmd.exe) or PowerShell window and run the following commands:
    ```bash
    python --version
    pip --version
    ```
    You should see the installed Python and pip versions printed to the console.

## 2. Create Virtual Environment

*   **Create Project Directory:**
    Open Command Prompt or PowerShell and create a directory for the project:
    ```bash
    mkdir airunner_project
    cd airunner_project
    ```
*   **Create Virtual Environment:**
    Inside the `airunner_project` directory, create a Python virtual environment. Using `.venv` as the environment name is a common convention:
    ```bash
    python -m venv .venv
    ```
*   **Activate Virtual Environment:**
    Activate the virtual environment. The command differs slightly between Command Prompt and PowerShell:
    *   **Command Prompt:**
        ```bash
        .venv\Scripts\activate
        ```
    *   **PowerShell:**
        ```bash
        .venv\Scripts\Activate.ps1
        ```
    Your command prompt should now show the virtual environment name (e.g., `(.venv) C:\path\to\airunner_project>`).

## 3. Install Dependencies

*   **Core Dependencies:**
    The project's core dependencies are listed in `setup.py`. With the virtual environment activated, install them using pip:
    ```bash
    pip install accelerate==1.7.0 "huggingface-hub>=0.24.0,<1.0" tokenizers==0.21.1 optimum==1.25.1 numpy==2.2.5 pillow==10.4.0 alembic==1.15.2 aiosqlite==0.21.0 sqlalchemy==2.0.38 setuptools==78.1.1 "etils[epath]==1.12.2" torchao
    ```
    *(Note: `torch`, `torchvision`, and `torchaudio` are handled separately below due to CUDA considerations. `torchao` is listed here as it's a smaller PyTorch-related library.)*

*   **PyTorch Installation (Crucial Step):**

    *   **Determine GPU and CUDA Availability:**
        If you have an NVIDIA GPU, you need to know your CUDA toolkit version. If you don't have an NVIDIA GPU or don't need GPU acceleration for your initial setup, you will install the CPU-only version.

    *   **Option A: Installing PyTorch with CUDA support (NVIDIA GPU required):**
        1.  Visit the [PyTorch Get Started page](https://pytorch.org/get-started/locally/).
        2.  Select the appropriate options for your system:
            *   PyTorch Build: Stable
            *   Your OS: Windows
            *   Package: Pip
            *   Language: Python
            *   Compute Platform: Select the CUDA version that matches your installed NVIDIA drivers and CUDA toolkit (e.g., CUDA 11.8, CUDA 12.1).
        3.  The website will generate a command. It will look something like this (example for CUDA 12.1):
            ```bash
            pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
            ```
            Run this command in your activated virtual environment.

    *   **Option B: Installing CPU-only PyTorch:**
        If you don't have an NVIDIA GPU or prefer a CPU-only version for now, use the following command:
        ```bash
        pip install torch torchvision torchaudio
        ```
        (You can also select the CPU option on the PyTorch Get Started page to get the exact command.)

*   **Verify PyTorch Installation:**
    Create a Python script (e.g., `verify_pytorch.py`) with the following content:
    ```python
    import torch

    print(f"PyTorch Version: {torch.__version__}")
    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available: {cuda_available}")
    if cuda_available:
        print(f"CUDA Version: {torch.version.cuda}")
        print(f"Current CUDA Device: {torch.cuda.current_device()}")
        print(f"Device Name: {torch.cuda.get_device_name(torch.cuda.current_device())}")
    else:
        print("CUDA not available or PyTorch CPU version installed.")
    ```
    Run this script from your activated virtual environment:
    ```bash
    python verify_pytorch.py
    ```
    The output will show your PyTorch version and whether CUDA is available.

## 4. Challenges and Notes for This Simulated Setup

*   **Python Version:** The target Python version was 3.13.3. In this simulated environment, Python 3.10.17 was available and used for conceptual command generation. Users should install the recommended version on their actual Windows machines.
*   **Virtual Environment Creation:** The command `python -m venv .venv` could not be run directly in the `run_in_bash_session` tool due to its nature. Users should run this command on their local machines as described.
*   **Dependency Installation Failure (Simulated Environment):**
    Attempts to install the full list of dependencies, and even PyTorch separately, failed in this simulated environment due to a persistent **"No space left on device"** error. This is a limitation of the sandboxed execution environment and **not reflective of a typical Windows setup experience** (assuming sufficient disk space).
*   **Guidance for Real Machines:** Users on a standard Windows 11 machine with adequate disk space should be able to install these packages using the `pip install` commands provided. The key is to ensure the PyTorch command matches their system's CUDA capabilities (if any).
*   **Final Package Versions:** Due to the installation failures in this environment, a list of final installed package versions cannot be provided from this simulation. Users should check the versions on their machines after successful installation using `pip freeze`.

This guide provides the *intended* steps for setting up the airunner development environment on Windows 11. The primary blocker in this simulated execution was insufficient disk space for large packages like PyTorch.
