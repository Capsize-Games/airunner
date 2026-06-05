#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DAEMON_PORT="${AIRUNNER_DAEMON_PORT:-8188}"
FAILURES=0

check() {
    local label="$1"
    local url="$2"
    local expected="${3:-}"

    echo -n "  ${label}: "
    local response
    response="$(curl -s --max-time 3 "${url}" 2>/dev/null || true)"

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
check "TTS WS            " "http://localhost:${DAEMON_PORT}/api/v1/tts/ws"
check "STT WS            " "http://localhost:${DAEMON_PORT}/api/v1/stt/stream"
check "Art WS            " "http://localhost:${DAEMON_PORT}/api/v1/art/ws"
check "Events WS         " "http://localhost:${DAEMON_PORT}/api/v1/events"
check "Daemon status     " "http://localhost:${DAEMON_PORT}/api/v1/daemon/status"

echo ""
if (( FAILURES > 0 )); then
    echo "❌ ${FAILURES} check(s) failed."
    exit 1
else
    echo "✅ All checks passed."
fi
