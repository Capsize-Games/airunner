#!/usr/bin/bash
# This script should be called from within docker to kick off a build
set -e  # Exit immediately if a command exits with a non-zero status

DISABLE_TELEMETRY=1
cd /app

echo ""
echo "============================================"
echo "Installing dependencies"
echo "============================================"
echo ""
python3 /app/dobuild.py

echo ""
echo "============================================"
echo "Build airunner for linux"
echo "============================================"
echo ""
DEV_ENV=0 AIRUNNER_ENVIRONMENT="prod" PYTHONOPTIMIZE=0 python3 -m PyInstaller --log-level=INFO --noconfirm /app/airunner.spec 2>&1 | tee build.log

# Create a function for error handling
handle_error() {
    echo "Error occurred during build process. Check build.log for details."
    exit 1
}

# Create a function to copy dependencies
copy_dependency() {
    local src=$1
    local dest=$2
    local name=$3
    
    echo ""
    echo "============================================"
    echo "Copy $name to dist"
    echo "============================================"
    echo ""
    
    if [ -e "$src" ]; then
        cp -R "$src" "$dest" || handle_error
        echo "Successfully copied $name"
    else
        echo "Warning: $name not found at $src"
    fi
}

# Copy required dependencies
copy_dependency "/home/appuser/.local/lib/python3.10/site-packages/timm" "./dist/airunner/" "timm"
copy_dependency "/home/appuser/.local/lib/python3.10/site-packages/torch/lib/libtorch_cuda_linalg.so" "./dist/airunner/" "libtorch_cuda_linalg.so"
copy_dependency "/app/setup.py" "./dist/airunner/" "setup.py"

# Find the correct Pillow dist-info directory
PILLOW_DIR=$(find /home/appuser/.local/lib/python3.10/site-packages -name "pillow-*.dist-info" -type d | head -n 1)
if [ -n "$PILLOW_DIR" ]; then
    copy_dependency "$PILLOW_DIR" "./dist/airunner/" "pillow dist-info"
else
    echo "Warning: Pillow dist-info directory not found"
fi

echo ""
echo "============================================"
echo "Deploying airunner to itch.io"
echo "============================================"
echo ""

# Ensure permissions are correct
chown -R 1000:1000 dist

# Get version from setup.py
LATEST_TAG=$(grep -oP '(?<=version=).*(?=,)' /app/setup.py | tr -d '"')
if [ -z "$LATEST_TAG" ]; then
    echo "Error: Could not extract version tag from setup.py"
    handle_error
fi
echo "Latest tag: $LATEST_TAG"

# Download and deploy using butler
wget -q https://dl.itch.ovh/butler/linux-amd64/head/butler && chmod +x butler
./butler push ./dist/airunner capsizegames/ai-runner:ubuntu --userversion "$LATEST_TAG"

echo ""
echo "============================================"
echo "Build and deployment complete!"
echo "============================================"
echo ""
