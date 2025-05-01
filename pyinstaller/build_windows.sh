#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Define the spec file path relative to the script location (pyinstaller/)
SPEC_FILE="airunner.windows.spec"
DIST_PATH="../dist" # Output directory relative to script location
BUILD_PATH="../build" # Build directory relative to script location

echo "Starting PyInstaller Windows build..."

# Navigate to the directory containing this script (pyinstaller/)
cd "$(dirname "$0")"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf ${DIST_PATH}/airunner_windows
rm -rf ${BUILD_PATH}/airunner

# Run PyInstaller using Wine with xvfb to provide virtual display
# The paths inside the spec file assume the context of the Wine environment
echo "Running PyInstaller via Wine..."
xvfb-run -a wine64 C:\\Python310\\Scripts\\pyinstaller.exe --noconfirm --distpath ${DIST_PATH} --workpath ${BUILD_PATH} ${SPEC_FILE}

echo "PyInstaller Windows build completed."
echo "Output located in ${DIST_PATH}/airunner_windows"

# Copy any additional required files to the output directory
echo "Copying additional files to output directory..."
# Add any necessary cp commands here if needed

echo "Build script finished."
