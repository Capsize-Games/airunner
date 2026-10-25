#!/bin/bash
# Docker entrypoint for AI Runner (headless services only)
#
# Usage:
#   docker compose run --rm airunner
#   docker compose run --rm airunner --port 8080

set -e

# Strip a legacy --headless flag if present; headless is now the only mode.
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
