#!/bin/bash
# Docker entrypoint for AI Runner
# Supports both GUI and headless modes
#
# Usage:
#   GUI mode (default):  docker compose run --rm airunner
#   Headless mode:       docker compose run --rm airunner --headless
#   Headless with args:  docker compose run --rm airunner --headless --port 9000

set -e

# Check if --headless flag is present
HEADLESS=0
HEADLESS_ARGS=""

for arg in "$@"; do
    if [ "$arg" = "--headless" ]; then
        HEADLESS=1
    fi
done

if [ "$HEADLESS" = "1" ]; then
    # Remove --headless from args and pass the rest to airunner-headless
    HEADLESS_ARGS=""
    for arg in "$@"; do
        if [ "$arg" != "--headless" ]; then
            HEADLESS_ARGS="$HEADLESS_ARGS $arg"
        fi
    done
    
    # Set headless environment
    export AIRUNNER_HEADLESS=1
    
    # Default to 0.0.0.0:8080 if no host/port specified
    if [[ ! "$HEADLESS_ARGS" =~ "--host" ]]; then
        HEADLESS_ARGS="--host 0.0.0.0 $HEADLESS_ARGS"
    fi
    if [[ ! "$HEADLESS_ARGS" =~ "--port" ]]; then
        HEADLESS_ARGS="--port 8080 $HEADLESS_ARGS"
    fi
    
    echo "Starting AI Runner in headless mode..."
    exec airunner-headless $HEADLESS_ARGS
else
    # GUI mode
    export AIRUNNER_HEADLESS=0
    
    echo "Starting AI Runner GUI..."
    exec airunner "$@"
fi
