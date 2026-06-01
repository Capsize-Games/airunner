#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LAUNCHER_BIN="${ROOT_DIR}/build/airunner-launcher/airunner"

if [[ ! -x "${LAUNCHER_BIN}" ]]; then
    echo "Native launcher not found at ${LAUNCHER_BIN}" >&2
    echo "Run ./scripts/dev/build.sh first." >&2
    exit 1
fi

echo "=== Starting AI Runner GUI ==="

export AIRUNNER_LOG_LEVEL="${AIRUNNER_LOG_LEVEL:-INFO}"
export AIRUNNER_DISABLE_STALE_DAEMON_CHECK=1

exec "${LAUNCHER_BIN}" \
    --mode dev \
    --repo-root "${ROOT_DIR}" \
    "$@"
