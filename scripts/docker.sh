#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Convenience wrapper around the dev Docker stack (open-core).
#
# Auto-detects an NVIDIA GPU and layers in docker-compose.gpu.yml when present,
# so `./scripts/docker.sh up` "just works" on both GPU and CPU machines.
#
# Usage:
#   ./scripts/docker.sh up [--client]   # start stack (+ Vite dev server)
#   ./scripts/docker.sh down            # stop stack
#   ./scripts/docker.sh build           # rebuild the server image
#   ./scripts/docker.sh logs [service]  # tail logs
#   ./scripts/docker.sh migrate         # run DB migrations once
#   ./scripts/docker.sh shell           # shell in the server container
#   ./scripts/docker.sh psql            # psql into the database
#   ./scripts/docker.sh ps | restart | <any docker compose subcommand>
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

COMPOSE=(docker compose -f docker-compose.yml)

# Layer the GPU override in automatically when an NVIDIA GPU is visible,
# unless explicitly disabled with AIRUNNER_NO_GPU=1.
if [[ "${AIRUNNER_NO_GPU:-0}" != "1" ]] && command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    COMPOSE+=(-f docker-compose.gpu.yml)
    GPU_NOTE="(GPU enabled)"
else
    GPU_NOTE="(CPU only)"
fi

if [[ ! -f .env ]]; then
    echo "No .env found — copy .env.docker.example to .env first." >&2
    exit 1
fi

cmd="${1:-up}"
shift || true

case "${cmd}" in
    up)
        WANT_CLIENT=()
        for a in "$@"; do [[ "${a}" == "--client" ]] && WANT_CLIENT=(--profile client); done
        echo "Starting AI Runner dev stack ${GPU_NOTE}..."
        exec "${COMPOSE[@]}" "${WANT_CLIENT[@]}" up --build -d
        ;;
    down)    exec "${COMPOSE[@]}" down "$@" ;;
    build)   exec "${COMPOSE[@]}" build "$@" ;;
    logs)    exec "${COMPOSE[@]}" logs -f "$@" ;;
    migrate) exec "${COMPOSE[@]}" run --rm server \
                python -c "import sys; sys.path.insert(0,'/app/server/src'); from airunner_services.database.setup_database import setup_database; setup_database()" ;;
    shell)   exec "${COMPOSE[@]}" exec server bash ;;
    psql)    exec "${COMPOSE[@]}" exec db psql -U "${POSTGRES_USER:-airunner}" -d "${POSTGRES_DB:-airunner}" ;;
    auth)    # Account management for the auth extension, e.g.:
             #   ./scripts/docker.sh auth create-user --email a@b.c \
             #       --username admin --password 'secret123' --superuser
             #   ./scripts/docker.sh auth list
             exec "${COMPOSE[@]}" exec server \
                python -m extensions.auth.server.manage "$@" ;;
    *)       exec "${COMPOSE[@]}" "${cmd}" "$@" ;;
esac
