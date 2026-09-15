#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEV_VENV="${AIRUNNER_DEV_VENV:-${ROOT_DIR}/venv}"
DEV_VENV_PYTHON="${DEV_VENV}/bin/python"

if [[ ! -x "${DEV_VENV_PYTHON}" ]]; then
    echo "Developer Python not found at ${DEV_VENV_PYTHON}" >&2
    echo "Run ./scripts/install.sh first or set AIRUNNER_DEV_VENV." >&2
    exit 1
fi

echo "=== Starting AI Runner GUI ==="

export DEV_ENV=1
export AIRUNNER_LOG_LEVEL="${AIRUNNER_LOG_LEVEL:-INFO}"
# Stale-daemon self-healing was previously disabled, which masked daemons that
# started before code tree changes (e.g. the shared/airunner_common package
# consolidation) and thus carried a frozen sys.path without access to shared/.
# Re-enabling the check lets the dev_build_token mismatch logic auto-restart
# such daemons. See run_services.sh running_daemon_is_stale.
# export AIRUNNER_DISABLE_STALE_DAEMON_CHECK=1
export PYTHONPATH="${ROOT_DIR}/services/src:${ROOT_DIR}/src:${ROOT_DIR}/native/src:${ROOT_DIR}/shared${PYTHONPATH:+:${PYTHONPATH}}"

exec "${DEV_VENV_PYTHON}" -m airunner.launcher "$@"
