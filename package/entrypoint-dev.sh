#!/bin/bash
set -e

# Install the package in development mode
if [ ! -d "/home/appuser/.local/lib/python3.10/site-packages/airunner.egg-link" ]; then
  echo "Installing airunner package in development mode..."
  pip install --user -e .[gui,linux,dev,art,llm,llm_weather,tts]
  pip install --user -U timm
fi

# Check if DISPLAY is set, if not, start xvfb
if [ -z "$DISPLAY" ]; then
  echo "No X display found, starting a virtual one with Xvfb..."
  Xvfb :99 -screen 0 1024x768x24 &
  export DISPLAY=:99
  sleep 2 # Give Xvfb time to start
fi

# Execute the command passed to docker
echo "Executing command: $@"
exec "$@"
