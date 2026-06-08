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
# Parse flags
# --------------------------------------------------------------------
RUN_SERVER=false
RUN_CLIENT=false

for arg in "$@"; do
    case "${arg}" in
        --server) RUN_SERVER=true ;;
        --client) RUN_CLIENT=true ;;
        *)
            echo "Usage: $0 [--server] [--client]" >&2
            echo "  No flags  → start both server and client" >&2
            echo "  --server  → start server (daemon + API) only" >&2
            echo "  --client  → start client (Vite dev server) only" >&2
            exit 1
            ;;
    esac
done

# Default: start both if neither flag is given
if ! $RUN_SERVER && ! $RUN_CLIENT; then
    RUN_SERVER=true
    RUN_CLIENT=true
fi

# --------------------------------------------------------------------
# Resolve client port from .env
# --------------------------------------------------------------------
resolve_client_port() {
    if [[ -f "${ROOT_DIR}/.env" ]]; then
        grep -E '^VITE_PORT=' "${ROOT_DIR}/.env" | cut -d= -f2 | tr -d ' '
    fi
}
CLIENT_PORT="$(resolve_client_port)"
CLIENT_PORT="${CLIENT_PORT:-5173}"

# --------------------------------------------------------------------
# Server
# --------------------------------------------------------------------
if $RUN_SERVER; then
    run_step "Starting services" "${DEV_DIR}/run_services.sh"
    run_step "Testing services" "${DEV_DIR}/test_services.sh"
    echo ""
    echo -e "${GREEN}Server running on http://localhost:${AIRUNNER_DAEMON_PORT:-8188}${NC}"
fi

# --------------------------------------------------------------------
# Client
# --------------------------------------------------------------------
if $RUN_CLIENT; then
    if [[ ! -d "${WEB_DIR}/node_modules" ]]; then
        echo ""
        echo -e "${YELLOW}Installing web client dependencies...${NC}"
        (cd "${WEB_DIR}" && npm install) || fail "npm install failed"
    fi

    echo ""
    echo -e "${GREEN}=== Starting web client ===${NC}"
    echo "Web client starting on http://localhost:${CLIENT_PORT}"
    echo ""
    echo "Press Ctrl+C to stop."
    echo ""

    if $RUN_SERVER; then
        echo "Press Ctrl+C to stop all services."
        trap 'echo ""; echo -e "${GREEN}Shutting down...${NC}"; kill 0' EXIT
    fi

    # Start Vite dev server in background (Vite reads VITE_PORT from .env)
    (cd "${WEB_DIR}" && npm run dev -- --host 0.0.0.0) &

    # Wait for any child to exit
    wait
fi
