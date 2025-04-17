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

## Next Steps

Potential improvements to the build system:

1. **Caching Optimization** - Implement Docker layer caching for faster builds
2. **Multi-platform Support** - Extend the build system for Windows/macOS
3. **Dependency Updates** - Create automated dependency update system
4. **Build Metrics** - Add build time and size monitoring
5. **Quality Gates** - Add quality checks before deployment

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