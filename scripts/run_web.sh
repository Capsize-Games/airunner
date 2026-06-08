#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEV_DIR="${ROOT_DIR}/scripts/dev"
WEB_DIR="${ROOT_DIR}/client"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

fail() {
    echo -e "${RED}ERROR:${NC} $*" >&2
    exit 1
}

run_step() {
    local label="$1"
    shift
    echo ""
    echo -e "${GREEN}=== ${label} ===${NC}"
    "$@" || fail "${label} failed (exit code $?)"
}

# --------------------------------------------------------------------
# 1. Start services (daemon + API)
# --------------------------------------------------------------------
run_step "Starting services" "${DEV_DIR}/run_services.sh"

# --------------------------------------------------------------------
# 3. Health check
# --------------------------------------------------------------------
run_step "Testing services" "${DEV_DIR}/test_services.sh"

# --------------------------------------------------------------------
# 4. Install web client dependencies (if needed)
# --------------------------------------------------------------------
if [[ ! -d "${WEB_DIR}/node_modules" ]]; then
    echo ""
    echo -e "${YELLOW}Installing web client dependencies...${NC}"
    (cd "${WEB_DIR}" && npm install) || fail "npm install failed"
fi

# --------------------------------------------------------------------
# 5. Start web client dev server
# --------------------------------------------------------------------
# Read VITE_PORT from .env if present; default to 5173
if [[ -f "${ROOT_DIR}/.env" ]]; then
    # shellcheck disable=SC1090
    VITE_PORT=$(grep -E '^VITE_PORT=' "${ROOT_DIR}/.env" | cut -d= -f2 | tr -d ' ')
fi
CLIENT_PORT="${VITE_PORT:-5173}"

echo ""
echo -e "${GREEN}=== Starting web client ===${NC}"
echo "Services running on http://localhost:${AIRUNNER_DAEMON_PORT:-8188}"
echo "Web client starting on http://localhost:${CLIENT_PORT}"
echo ""
echo "Press Ctrl+C to stop all services."
echo ""

trap 'echo ""; echo -e "${GREEN}Shutting down...${NC}"; kill 0' EXIT

# Start Vite dev server in background (Vite reads VITE_PORT from .env)
(cd "${WEB_DIR}" && npm run dev -- --host 0.0.0.0) &

# Wait for any child to exit
wait
