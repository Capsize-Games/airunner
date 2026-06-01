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

current_dev_build_token() {
    PYTHONPATH="${ROOT_DIR}/services/src:${ROOT_DIR}/src:${ROOT_DIR}/native/src${PYTHONPATH:+:${PYTHONPATH}}" \
    DEV_ENV=1 \
    "${DEV_VENV_BIN}/python" - <<'PY'
from airunner_services.dev_build_token import current_dev_build_token

print(current_dev_build_token() or "")
PY
}

running_dev_build_token() {
    local health_payload
    health_payload="$(curl -s --max-time 2 "http://localhost:${DAEMON_PORT}/api/v1/health" 2>/dev/null || true)"
    if [[ -z "${health_payload}" ]]; then
        return
    fi
    printf '%s' "${health_payload}" | "${DEV_VENV_BIN}/python" - <<'PY'
import json
import sys

try:
    payload = json.load(sys.stdin)
except Exception:
    print("")
else:
    print(str(payload.get("dev_build_token") or ""))
PY
}

stop_running_daemon() {
    if [[ ! -f "${PID_FILE}" ]]; then
        return
    fi

    local pid
    pid="$(head -n1 "${PID_FILE}")"
    curl -s --max-time 2 -X POST \
        "http://localhost:${DAEMON_PORT}/admin/shutdown" \
        >/dev/null 2>&1 || true

    local deadline=$((SECONDS + 10))
    while (( SECONDS < deadline )); do
        if ! kill -0 "${pid}" 2>/dev/null; then
            rm -f "${PID_FILE}"
            return
        fi
        sleep 0.5
    done

    kill "${pid}" 2>/dev/null || true
    deadline=$((SECONDS + 5))
    while (( SECONDS < deadline )); do
        if ! kill -0 "${pid}" 2>/dev/null; then
            rm -f "${PID_FILE}"
            return
        fi
        sleep 0.5
    done

    rm -f "${PID_FILE}"
}

running_daemon_is_stale() {
    local expected_token
    local running_token

    expected_token="$(current_dev_build_token)"
    running_token="$(running_dev_build_token)"

    if [[ -z "${running_token}" ]]; then
        echo "Daemon is missing a dev build token or health payload; restarting."
        return 0
    fi

    if [[ -n "${expected_token}" && "${running_token}" != "${expected_token}" ]]; then
        echo "Daemon build token mismatch detected; restarting."
        return 0
    fi

    return 1
}

# --------------------------------------------------
# Launch daemon
# --------------------------------------------------
start_services() {
    if daemon_running; then
        if running_daemon_is_stale; then
            stop_running_daemon
        else
            echo "Daemon already running (PID $(head -n1 "${PID_FILE}"))"
            return
        fi
    fi

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
    export PYTHONPATH="${ROOT_DIR}/services/src:${ROOT_DIR}/src:${ROOT_DIR}/native/src${PYTHONPATH:+:${PYTHONPATH}}"
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
