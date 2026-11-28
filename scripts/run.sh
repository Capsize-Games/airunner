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

# 1. Start services (daemon + API)
run_step "Starting services" "${DEV_DIR}/run_services.sh"

# 2. Health check
run_step "Testing services" "${DEV_DIR}/test_services.sh"

# 3. Done (desktop GUI retired with src/ on 2026-10-25)
echo ""
echo -e "${GREEN}=== Services are running ===${NC}"
echo "Interact with the daemon on port 8188 (see deployment/systemd/README.md)."
echo "Use ${DEV_DIR}/stop_services.sh to stop."
