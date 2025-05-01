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

# Run PyInstaller using Wine
# The paths inside the spec file assume the context of the Wine environment
# Make sure WINEPREFIX and other Wine env vars are set correctly by the Docker environment
echo "Running PyInstaller via Wine..."
wine pyinstaller --noconfirm --distpath ${DIST_PATH} --workpath ${BUILD_PATH} ${SPEC_FILE}

echo "PyInstaller Windows build completed."
echo "Output located in ${DIST_PATH}/airunner_windows"

# Optional: Add steps here to create an installer (e.g., using Inno Setup within Wine)
# Example:
# if [ -f "setup.iss" ]; then
#   echo "Creating installer using Inno Setup..."
#   wine "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss
#   echo "Installer created."
# fi

# Optional: Add steps to copy additional files if needed
# Example:
# echo "Copying additional files..."
# cp some_other_file.txt ${DIST_PATH}/airunner_windows/

echo "Build script finished."
