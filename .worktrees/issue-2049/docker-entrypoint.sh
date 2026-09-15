#!/bin/bash
# Docker entrypoint for AI Runner
# Supports both GUI and headless modes
#
# Usage:
#   GUI mode (default):  docker compose run --rm airunner
#   Headless mode:       docker compose run --rm airunner --headless
#   Headless with args:  docker compose run --rm airunner --headless --port 8080

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
    
    # Bind to loopback by default unless AIRUNNER_HEADLESS_HOST is set.
    # Binding to 0.0.0.0 exposes the API without authentication; require an
    # explicit opt-in (AIRUNNER_HEADLESS_HOST) or --host flag for that.
    DEFAULT_HOST="${AIRUNNER_HEADLESS_HOST:-127.0.0.1}"
    if [[ ! "$HEADLESS_ARGS" =~ "--host" ]]; then
        HEADLESS_ARGS="--host $DEFAULT_HOST $HEADLESS_ARGS"
    fi
    if [[ ! "$HEADLESS_ARGS" =~ "--port" ]]; then
        HEADLESS_ARGS="--port 8080 $HEADLESS_ARGS"
    fi
    
    echo "Starting AI Runner in headless mode..."
    # NOTE: Dev reload (AIRUNNER_DEV_RELOAD=1) previously exec'd
    # `python3.13 -m airunner.dev.autorestart`, but no such module exists in
    # this tree, so the block was removed (issue #2063). The flag is now
    # ignored; a warning is printed so users are not misled into thinking
    # auto-restart is active.
    if [ "${AIRUNNER_DEV_RELOAD:-0}" = "1" ]; then
        echo "WARNING: AIRUNNER_DEV_RELOAD is not supported (no autoreload module exists); starting without reload." >&2
    fi
    exec airunner-headless $HEADLESS_ARGS
else
    # GUI mode
    export AIRUNNER_HEADLESS=0
    
    echo "Starting AI Runner GUI..."
    exec airunner "$@"
fi
