# AiRunner Build Process Documentation

## Overview

AiRunner uses a three-stage Docker build process to create distributable packages:

1. **Base Image** - Contains system dependencies and tools needed for building
2. **Runtime Image** - Contains Python dependencies and runtime environment 
3. **Package Build** - Creates the final PyInstaller package

This build process is designed to work with GitHub Actions and can run on self-hosted runners in a secure, isolated manner.

## Build Modes

The build system supports two modes:

1. **Standard Mode** - Uses volume mounts for development
2. **CI Mode** - Fully containerized without volume mounts

## Build Process Steps

### 1. Base Image Build

The base image contains all system dependencies and tools required for building AiRunner.

```bash
./src/airunner/bin/docker.sh --ci build_base
```

This creates `ghcr.io/capsize-games/airunner/airunner:linux_ci`.

### 2. Runtime Image Build

The runtime image installs Python dependencies on top of the base image.

```bash
./src/airunner/bin/docker.sh --ci build_runtime
```

This creates `ghcr.io/capsize-games/airunner/airunner:linux_build_runtime_ci`.

### 3. Package Build

The package build creates the final PyInstaller package.

```bash
./src/airunner/bin/docker.sh --ci build_package
```

This creates the final application in `./dist/`.

## CI/CD Pipeline

The build process is automated through GitHub Actions:

1. When code is pushed to `master`, the `docker-release.yml` workflow builds the base image
2. When a release is published, the `linux-dispatch.yml` workflow builds the runtime image and package

## Using the Build System

### Local Development

For local development with volume mounts:

```bash
./src/airunner/bin/docker.sh build_base
./src/airunner/bin/docker.sh build_runtime
./src/airunner/bin/docker.sh build_package
```

### CI Mode (Isolated)

For CI or isolated builds:

```bash
./src/airunner/bin/docker.sh --ci build_base
./src/airunner/bin/docker.sh --ci build_runtime
./src/airunner/bin/docker.sh --ci build_package
```

## Testing the Build System

Run the automated test script:

```bash
./test_ci_mode.sh
```

This script validates:
- Image building
- File system isolation
- Package creation
- Configuration correctness

## Clean Up

To clean up Docker images and containers:

```bash
# Stop and remove containers
docker ps -a | grep "airunner_" | awk '{print $1}' | xargs -r docker rm -f

# Remove images 
docker images | grep "airunner" | awk '{print $1":"$2}' | xargs -r docker rmi -f

# Clean build artifacts
rm -rf ./dist/* ./build/*
```

## Building on Windows

This section describes the process for creating a distributable package of AiRunner on Windows using PyInstaller. This is separate from the Docker-based build process used for Linux.

### Prerequisites for Building on Windows:
1.  **Python:** Ensure Python (version specified in `setup.py`, e.g., 3.13+) is installed.
2.  **Virtual Environment:** It is highly recommended to create and activate a Python virtual environment for the build to isolate dependencies.
3.  **Project Cloned/Downloaded:** You need the full AiRunner source code.
4.  **Dependencies Installed:** Install project dependencies, including `pyinstaller`:
    ```batch
    REM Activate your virtual environment first
    python -m pip install --upgrade pip setuptools wheel
    python -m pip install -r requirements.txt  # Or install via setup.py extras if preferred
    python -m pip install pyinstaller==6.12.0
    ```
    (Note: You might install dependencies using `pip install .[all_dev]` or similar from the project root, which should include PyInstaller if it's in `dev` extras).

### Build Steps:
1.  **Navigate to Project Root:** Open a command prompt or PowerShell window and navigate to the root directory of the AiRunner project (where `airunner.spec` and `build_windows.bat` are located).
2.  **Activate Virtual Environment:** If you haven't already, activate your Python virtual environment.
3.  **Run the Build Script:** Execute the Windows build batch script:
    ```batch
    build_windows.bat
    ```
    This script will:
    *   Install the correct version of PyInstaller.
    *   Run PyInstaller using the `airunner.spec` file.
    *   Place the output in the `./dist_windows` directory.
    *   Store intermediate build files in `./build_windows`.

The `airunner.spec` file contains all the configurations for PyInstaller, including hidden imports, data files (like `.ui` files, icons, `mathjax`, and documentation), and executable settings.

## Next Steps

Potential improvements to the build system:

1. **Caching Optimization (Docker)** - Implement Docker layer caching for faster Linux builds.
2. **Multi-platform CI** - Further integrate Windows builds into CI/CD pipelines (e.g., using GitHub Actions with Windows runners). The current `build_windows.bat` is a step towards this.
3. **Dependency Updates** - Create an automated dependency update system for both Linux and Windows setups.
4. **Build Metrics** - Add build time and size monitoring for both platforms.
5. **Quality Gates** - Add quality checks before deployment for both platforms.

## Troubleshooting

### Common Issues

1. **Permission Denied** - Check user/group IDs in the .env file
2. **Missing Dependencies** - Check that the base image has all required system packages
3. **PyInstaller Errors** - Review build logs in `./build/airunner.log`

### Logs

Build logs are available in:
- Runtime build: Container logs
- Package build: `./build/build.log`
- Test results: `./ci_mode_test_results.log`