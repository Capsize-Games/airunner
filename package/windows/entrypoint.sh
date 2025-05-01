#!/bin/bash
# Ensure the user owns the wine prefix and app directory
# This might be necessary if volumes are mounted with root ownership initially
sudo chown -R wineuser:wineuser /home/wineuser/.wine /app

# Execute the command passed to the container using gosu to step down from root
# If the container is run as root, this switches to the wineuser
# If the container is already run as wineuser, this effectively just runs the command
if [ "$(id -u)" = "0" ]; then
  exec gosu wineuser "$@"
else
  exec "$@"
fi
