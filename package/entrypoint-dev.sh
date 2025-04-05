#!/bin/bash
set -e

echo "===== X11 Setup Diagnostic Information ====="
echo "User: $(whoami)"
echo "DISPLAY: $DISPLAY"
echo "XAUTHORITY: $XAUTHORITY"
echo "Checking X11 socket directory:"
ls -la /tmp/.X11-unix/
echo "Checking if .Xauthority exists:"
ls -la $XAUTHORITY 2>/dev/null || echo ".Xauthority not found"

# Check if we can connect to the X server
echo "Testing X connection with xdpyinfo:"
xdpyinfo >/dev/null 2>&1 && echo "X connection successful!" || echo "X connection failed"

exec "$@"