#!/bin/bash
# Simple test server runner - logs to /tmp/test_server.log

LOG_FILE="/tmp/test_server.log"

echo "Starting AI Runner test server..."
echo "Log file: $LOG_FILE"
echo ""

# Clear old log
> "$LOG_FILE"

# Run server with logging
cd "$(dirname "$0")"
python test_headless_worker.py 2>&1 | tee "$LOG_FILE"
