#!/bin/bash
set -e

# Install the package in development mode
if [ ! -d "/home/appuser/.local/lib/python3.10/site-packages/airunner.egg-link" ]; then
  echo "Installing airunner package in development mode..."
  pip install --user -e .[gui,linux,dev,art,llm,llm_weather,tts]
  pip install --user --upgrade timm==1.0.15
fi

# Execute the command passed to docker
exec "$@"
