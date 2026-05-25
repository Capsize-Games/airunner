#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PID_FILE="${ROOT_DIR}/build/airunner-services.pid"
LOG_DIR="${ROOT_DIR}/build/logs"
DAEMON_PORT="${AIRUNNER_DAEMON_PORT:-8188}"
DEV_VENV="${AIRUNNER_DEV_VENV:-${ROOT_DIR}/venv}"
DEV_VENV_BIN="${DEV_VENV}/bin"
SIDECAR_BIN_DIR="${ROOT_DIR}/build/runtime-sidecars/linux/bin"

mkdir -p "${LOG_DIR}"

if [[ ! -x "${DEV_VENV_BIN}/python" ]]; then
    echo "Developer Python not found at ${DEV_VENV_BIN}/python" >&2
    echo "Run ./scripts/install.sh first or set AIRUNNER_DEV_VENV." >&2
    exit 1
fi

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
    export PATH="${DEV_VENV_BIN}:${SIDECAR_BIN_DIR}${PATH:+:${PATH}}"

    if [[ -x "${SIDECAR_BIN_DIR}/llama-server" ]]; then
        export AIRUNNER_LLAMA_SERVER_BIN="${SIDECAR_BIN_DIR}/llama-server"
    fi
    if [[ -x "${SIDECAR_BIN_DIR}/whisper-server" ]]; then
        export AIRUNNER_WHISPER_SERVER_BIN="${SIDECAR_BIN_DIR}/whisper-server"
    fi

    "${DEV_VENV_BIN}/python" -m airunner_services.daemon \
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
start_services

echo ""
echo "=== Services running ==="
echo "  Health:  http://localhost:${DAEMON_PORT}/api/v1/health"
echo "  API docs: http://localhost:${DAEMON_PORT}/api/v1/docs"
echo "  Logs:    ${LOG_DIR}/daemon.log"
