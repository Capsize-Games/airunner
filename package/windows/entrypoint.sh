#!/bin/bash
# Ensure permissions are set correctly for Wine directories
sudo chown -R wineuser:wineuser /home/wineuser/.wine 

# Ensure app directory is writable
if [ -d "/app" ]; then
  sudo chown -R wineuser:wineuser /app
fi

# Try to clean up any stale X lock files
sudo rm -rf /tmp/.X*-lock 2>/dev/null || true

# Execute the command as wineuser
exec "$@"
