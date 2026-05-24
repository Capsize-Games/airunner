#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PID_FILE="${ROOT_DIR}/build/airunner-services.pid"

echo "=== Stopping AI Runner services ==="

# Stop tracked daemon via PID file
if [[ -f "${PID_FILE}" ]]; then
    pid="$(head -n1 "${PID_FILE}")"
    if kill -0 "${pid}" 2>/dev/null; then
        echo "Stopping daemon (PID ${pid})..."
        kill -TERM "${pid}" 2>/dev/null || true

        deadline=$((SECONDS + 5))
        while kill -0 "${pid}" 2>/dev/null; do
            if (( SECONDS >= deadline )); then
                echo "Force-killing daemon..."
                kill -KILL "${pid}" 2>/dev/null || true
                break
            fi
            sleep 0.2
        done
    fi
    rm -f "${PID_FILE}"
    echo "Daemon stopped."
else
    echo "No PID file found at ${PID_FILE}"
fi

# Clean up any lingering daemon processes
if pkill -f "airunner_services.daemon" 2>/dev/null; then
    echo "Cleaned up lingering daemon processes."
fi

echo "All services stopped."
