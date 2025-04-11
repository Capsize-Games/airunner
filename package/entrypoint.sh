#!/bin/bash
set -e
set -x

# Set PYTHONUSERBASE to ensure pip installs packages into the correct directory
export PYTHONUSERBASE=/home/appuser/.local/share/airunner/python
export PATH=/home/appuser/.local/share/airunner/python/bin:$PATH

# Ensure the PATH includes the bin directory under PYTHONUSERBASE
export PATH=$PYTHONUSERBASE/bin:$PATH

# Update PYTHONPATH to include the dist-packages directory under PYTHONUSERBASE
export PYTHONPATH=$PYTHONUSERBASE/local/lib/python3.10/dist-packages:$PYTHONPATH

# Remove PIP_USER to avoid conflicts with --prefix
unset PIP_USER

# Ensure pip uses the correct cache directory
export PIP_CACHE_DIR=$AIRUNNER_HOME_DIR/.cache/pip

echo "PATH set to $PATH"
echo "PYTHONPATH set to $PYTHONPATH"
echo "PIP_CACHE_DIR set to $PIP_CACHE_DIR"

# Diagnostic information
echo "PYTHONUSERBASE set to $PYTHONUSERBASE"

# Ensure the directory structure exists (but don't try to chmod mounted volumes)
mkdir -p $PYTHONUSERBASE/{bin,lib,share}

# Diagnostic information
echo "User: $(whoami)"
echo "PYTHONUSERBASE: $PYTHONUSERBASE"

# Diagnostic information for X11 setup
echo "===== X11 Setup Diagnostic Information ====="
echo "DISPLAY: $DISPLAY"
echo "XAUTHORITY: $XAUTHORITY"
echo "Checking X11 socket directory:"
ls -la /tmp/.X11-unix/ || echo "X11 socket directory not found"
echo "Checking if .Xauthority exists:"
ls -la $XAUTHORITY 2>/dev/null || echo ".Xauthority not found"

# Check if we can connect to the X server
echo "Testing X connection with xdpyinfo:"
if xdpyinfo >/dev/null 2>&1; then
  echo "X connection successful!"
else
  echo "X connection failed"
fi

/app/package/install_python_packages.sh

# Modify the script to handle interactive sessions properly
if [ "$#" -eq 0 ]; then
  echo "No command provided. Starting an interactive shell..."
  exec bash
else
  echo "Executing command: $@"
  exec "$@"
fi