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

# An NVIDIA GPU is present and the driver is loaded? Detect via several
# signals, since `nvidia-smi` is not always on PATH even when the driver and
# device nodes exist (e.g. open-kernel-module installs).
host_has_nvidia_gpu() {
    { command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; } && return 0
    [[ -e /dev/nvidia0 ]] && return 0               # driver device node
    [[ -f /proc/driver/nvidia/version ]] && return 0 # kernel module loaded
    return 1
}

# Can Docker actually pass a GPU through? Requires nvidia-container-toolkit,
# which registers the `nvidia` runtime / CDI with the Docker daemon.
docker_gpu_ready() {
    docker info 2>/dev/null | grep -qiE '(^| )nvidia' && return 0
    command -v nvidia-ctk >/dev/null 2>&1 && return 0
    return 1
}

# Layer the GPU override in automatically, unless explicitly disabled with
# AIRUNNER_NO_GPU=1. If a GPU exists but Docker can't reach it, say so loudly
# and fall back to CPU instead of either silently degrading or hard-failing.
if [[ "${AIRUNNER_NO_GPU:-0}" == "1" ]]; then
    GPU_NOTE="(CPU only — AIRUNNER_NO_GPU=1)"
elif host_has_nvidia_gpu; then
    if docker_gpu_ready; then
        COMPOSE+=(-f docker-compose.gpu.yml)
        GPU_NOTE="(GPU enabled)"
    else
        GPU_NOTE="(CPU only)"
        cat >&2 <<'WARN'
[docker.sh] An NVIDIA GPU is present but Docker cannot access it — the
           nvidia-container-toolkit is not installed/configured, so the GPU
           override was skipped and the stack will run on CPU.

           To enable GPU (Debian/Ubuntu host):
             curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
               | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
             curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
               | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#' \
               | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
             sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
             sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker

           Then re-run this command. See docker/README.md (GPU section).
WARN
    fi
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
