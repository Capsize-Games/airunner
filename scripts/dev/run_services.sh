#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PID_FILE="${ROOT_DIR}/build/airunner-services.pid"
LOG_DIR="${ROOT_DIR}/build/logs"
DAEMON_PORT="${AIRUNNER_DAEMON_PORT:-8188}"

mkdir -p "${LOG_DIR}"

# --------------------------------------------------
# Helpers
# --------------------------------------------------
daemon_running() {
    if [[ -f "${PID_FILE}" ]]; then
        local pid
        pid="$(head -n1 "${PID_FILE}")"
        if kill -0 "${pid}" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# --------------------------------------------------
# Stop existing daemon if running
# --------------------------------------------------
stop_services() {
    echo "=== Stopping AI Runner services ==="

    if [[ -f "${PID_FILE}" ]]; then
        local pid
        pid="$(head -n1 "${PID_FILE}")"
        if kill -0 "${pid}" 2>/dev/null; then
            echo "Stopping daemon (PID ${pid})..."
            kill -TERM "${pid}" 2>/dev/null || true

            # Wait up to 5s for graceful shutdown
            local deadline=$((SECONDS + 5))
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
    fi

    # Clean up any leftover daemon processes
    pkill -f "airunner_services.daemon" 2>/dev/null || true
    echo "Services stopped."
}

# --------------------------------------------------
# Launch daemon
# --------------------------------------------------
start_services() {
    if daemon_running; then
        echo "Daemon already running (PID $(head -n1 "${PID_FILE}"))"
        return
    fi

    echo "=== Starting AI Runner daemon ==="
    echo "Log: ${LOG_DIR}/daemon.log"

    export DEV_ENV=1
    export AIRUNNER_HEADLESS=1
    export AIRUNNER_SD_ON=1
    export AIRUNNER_LOG_LEVEL="${AIRUNNER_LOG_LEVEL:-INFO}"
    export AIRUNNER_DISABLE_STALE_DAEMON_CHECK=1
    export PYTHONPATH="${ROOT_DIR}/services/src:${ROOT_DIR}/api/src:${ROOT_DIR}/model/src:${ROOT_DIR}/src:${ROOT_DIR}/native/src${PYTHONPATH:+:${PYTHONPATH}}"

    "${ROOT_DIR}/venv/bin/python" -m airunner_services.daemon \
        > "${LOG_DIR}/daemon.log" 2>&1 &

    local daemon_pid=$!
    echo "${daemon_pid}" > "${PID_FILE}"
    echo "Daemon started (PID ${daemon_pid})"

    # Wait for health check
    echo -n "Waiting for daemon to become ready..."
    local deadline=$((SECONDS + 30))
    while (( SECONDS < deadline )); do
        if curl -s --max-time 1 "http://localhost:${DAEMON_PORT}/api/v1/health" >/dev/null 2>&1; then
            echo " ready!"
            return
        fi
        echo -n "."
        sleep 0.5
    done

    echo ""
    echo "WARNING: Daemon did not respond to health check within 30s."
    echo "Check ${LOG_DIR}/daemon.log for details."
}

# --------------------------------------------------
# Main
# --------------------------------------------------
stop_services
start_services

echo ""
echo "=== Services running ==="
echo "  Health:  http://localhost:${DAEMON_PORT}/api/v1/health"
echo "  API docs: http://localhost:${DAEMON_PORT}/api/v1/docs"
echo "  Logs:    ${LOG_DIR}/daemon.log"
