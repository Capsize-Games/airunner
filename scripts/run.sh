#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEV_DIR="${ROOT_DIR}/scripts/dev"
WEB_DIR="${ROOT_DIR}/airunner_web_client"

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

# 1. Build the native launcher
run_step "Building native launcher" "${DEV_DIR}/build.sh" "$@"

# 2. Start services (daemon + API)
run_step "Starting services" "${DEV_DIR}/run_services.sh"

# 3. Health check
run_step "Testing services" "${DEV_DIR}/test_services.sh"

# 4. Install web client dependencies (if needed)
if [[ ! -d "${WEB_DIR}/node_modules" ]]; then
    echo ""
    echo -e "${YELLOW}Installing web client dependencies...${NC}"
    (cd "${WEB_DIR}" && npm install) || fail "npm install failed"
fi

# 5. Launch web GUI
echo ""
echo -e "${GREEN}=== Launching Web GUI ===${NC}"
echo "Daemon running on port ${AIRUNNER_DAEMON_PORT:-8188}."
echo "Web GUI starting on http://localhost:5173"
echo "Press Ctrl+C to stop."
echo ""

(cd "${WEB_DIR}" && npm run dev -- --host 0.0.0.0)
