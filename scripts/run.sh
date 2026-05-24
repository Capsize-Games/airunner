#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEV_DIR="${ROOT_DIR}/scripts/dev"

RED='\033[0;31m'
GREEN='\033[0;32m'
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

# 4. Launch GUI
echo ""
echo -e "${GREEN}=== Launching GUI ===${NC}"
echo "Services are running. GUI will auto-connect to daemon on port 8188."
echo "Press Ctrl+C in the GUI to stop."
echo ""

exec "${DEV_DIR}/run_gui.sh"
