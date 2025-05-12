#!/bin/bash
set -e
set -x

# Check Python version first
echo "===== Python Version Check ====="
python --version
pip --version
if [ "$(python --version 2>&1 | cut -d ' ' -f 2 | cut -d '.' -f 1-2)" != "3.13" ]; then
  echo "ERROR: Required Python 3.13.x not found. Exiting."
  exit 1
fi
echo "✅ Python 3.13.x verified successfully!"

# Set PYTHONUSERBASE to ensure pip installs packages into the correct directory
export PYTHONUSERBASE=/home/appuser/.local/share/airunner/python
export PATH=/home/appuser/.local/share/airunner/python/bin:/home/appuser/.local/share/airunner/python/bin:$PATH
export PATH=$PYTHONUSERBASE/bin:$PATH

# Remove PIP_USER to avoid conflicts with --prefix
unset PIP_USER

# Ensure pip uses the correct cache directory
export PIP_CACHE_DIR=$AIRUNNER_HOME_DIR/.cache/pip

echo "PATH set to $PATH"
echo "PIP_CACHE_DIR set to $PIP_CACHE_DIR"

# Diagnostic information
echo "PYTHONUSERBASE set to $PYTHONUSERBASE"
echo "User: $(whoami)"

# Ensure the directory structure exists
mkdir -p $PYTHONUSERBASE/{bin,lib,share}

# Source bashrc for additional configurations
if [ -f /home/appuser/.bashrc ]; then
  echo "Loading configurations from .bashrc"
  . /home/appuser/.bashrc
fi

# Set up Wayland environment variables
export QT_QPA_PLATFORM=wayland
export QT_WAYLAND_DISABLE_WINDOWDECORATION=1
export QT_QPA_PLATFORMTHEME=gtk3
export GDK_BACKEND=wayland
export XDG_SESSION_TYPE=wayland

echo "===== Wayland Setup Information ====="
echo "XDG_SESSION_TYPE: $XDG_SESSION_TYPE"
echo "QT_QPA_PLATFORM: $QT_QPA_PLATFORM"
echo "GDK_BACKEND: $GDK_BACKEND"

# Handle interactive sessions
if [ "$#" -eq 0 ]; then
  echo "No command provided. Starting an interactive shell..."
  exec bash
else
  echo "Executing command: $@"
  exec "$@"
fi