#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DAEMON_PORT="${AIRUNNER_DAEMON_PORT:-8188}"
DEV_VENV="${AIRUNNER_DEV_VENV:-${ROOT_DIR}/venv}"
DEV_VENV_BIN="${DEV_VENV}/bin"
FAILURES=0

# Loopback auth (issue #2033) requires the X-Airunner-Token header on every
# non-health request. Without it the API middleware rejects the probe with 401
# *before* routing, so a GET on a POST-only endpoint would never reach the route
# that returns 405 "Method Not Allowed". Read the per-user token exactly like
# scripts/run_tests.py and the GUI daemon client do.
LOOPBACK_TOKEN=""
if [[ -x "${DEV_VENV_BIN}/python" ]]; then
    LOOPBACK_TOKEN="$(
        PYTHONPATH="${ROOT_DIR}/services/src:${ROOT_DIR}/shared" \
        "${DEV_VENV_BIN}/python" - <<'PY'
try:
    from airunner_services.api.loopback_token import (
        get_or_create_loopback_token,
    )
    print(get_or_create_loopback_token() or "")
except Exception:
    try:
        from airunner_common.settings import AIRUNNER_BASE_PATH
        from pathlib import Path
        token = (
            Path(AIRUNNER_BASE_PATH) / "config" / "loopback_token"
        ).read_text(encoding="utf-8").strip()
        print(token)
    except Exception:
        print("")
PY
    )"
fi

AUTH_ARGS=()
if [[ -n "${LOOPBACK_TOKEN}" ]]; then
    AUTH_ARGS=(-H "X-Airunner-Token: ${LOOPBACK_TOKEN}")
fi

check() {
    local label="$1"
    local url="$2"
    local expected="${3:-}"

    echo -n "  ${label}: "
    local response
    response="$(curl -s --max-time 3 "${AUTH_ARGS[@]}" "${url}" 2>/dev/null || true)"

    if [[ -z "${response}" ]]; then
        echo "FAIL (no response)"
        FAILURES=$((FAILURES + 1))
        return
    fi

    if [[ -n "${expected}" ]]; then
        if echo "${response}" | grep -q "${expected}"; then
            echo "OK"
        else
            echo "FAIL (expected '${expected}')"
            FAILURES=$((FAILURES + 1))
        fi
    else
        echo "OK"
    fi
}

echo "=== AI Runner Service Health Check ==="
echo "Daemon port: ${DAEMON_PORT}"
echo ""

check "Daemon health     " "http://localhost:${DAEMON_PORT}/api/v1/health" "healthy"
check "API root          " "http://localhost:${DAEMON_PORT}/api/v1/"
check "LLM chat          " "http://localhost:${DAEMON_PORT}/api/v1/llm/chat"
check "LLM models        " "http://localhost:${DAEMON_PORT}/api/v1/llm/models"
check "TTS synthesize    " "http://localhost:${DAEMON_PORT}/api/v1/tts/synthesize" "Method Not Allowed"
check "STT transcribe    " "http://localhost:${DAEMON_PORT}/api/v1/stt/transcribe" "Method Not Allowed"
check "Art generate      " "http://localhost:${DAEMON_PORT}/api/v1/art/generate" "Method Not Allowed"
check "Downloads         " "http://localhost:${DAEMON_PORT}/api/v1/downloads/url" "Method Not Allowed"
check "Daemon status     " "http://localhost:${DAEMON_PORT}/api/v1/daemon/status"

echo ""
if (( FAILURES > 0 )); then
    echo "❌ ${FAILURES} check(s) failed."
    exit 1
else
    echo "✅ All checks passed."
fi
