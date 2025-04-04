#!/bin/bash
set -e

# Install the package in development mode
# if [ ! -d "/home/appuser/.local/lib/python3.10/site-packages/airunner.egg-link" ]; then
#   echo "Installing airunner package in development mode..."
#   pip install --user -e .[gui,linux,dev,art,llm,llm_weather,tts]
#   pip install --user -U timm
# fi

# Start Xvfb ONCE explicitly!
Xvfb :1 -screen 0 1280x720x24 -ac +extension GLX +render -noreset &
sleep 3

# Verify if DISPLAY is available for debugging
if ! xdpyinfo -display :1 &> /dev/null; then
  echo "ERROR: Xvfb failed to start!"
  exit 1
else
  echo "Xvfb has started successfully at :1"
fi


# Execute the command passed to docker
echo "Executing command: $@"
exec "$@"
