#!/bin/bash
set -e

# Diagnostic information for X11 setup
echo "===== X11 Setup Diagnostic Information ====="
echo "User: $(whoami)"
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

# Modify the script to handle interactive sessions properly
if [ "$#" -eq 0 ]; then
  echo "No command provided. Starting an interactive shell..."
  exec bash
else
  echo "Executing command: $@"
  exec "$@"
fi