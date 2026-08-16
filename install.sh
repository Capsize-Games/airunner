#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${AIRUNNER_INSTALL_MODE:-dev}"
MODE_ARGS=()

log_error() {
    printf '[ERROR] %s\n' "$1" >&2
}


usage() {
    cat <<EOF
Usage: ./install.sh [options] [-- mode-specific args]

AIRunner is distributed as a Python application. Two installer modes exist:

  dev          Delegate to ./scripts/install.sh (repo development)
  distributed  Delegate to ./deployment/install_distributed.sh

Options:
  --mode MODE  dev|distributed
  -h, --help   Show this help text
EOF
}


parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --mode)
                MODE="$2"
                shift 2
                ;;
            -h|--help)
                MODE_ARGS+=("$1")
                shift
                ;;
            --)
                shift
                MODE_ARGS+=("$@")
                return
                ;;
            *)
                MODE_ARGS+=("$1")
                shift
                ;;
        esac
    done
}


main() {
    parse_args "$@"

    case "$MODE" in
        dev)
            exec "$ROOT_DIR/scripts/install.sh" "${MODE_ARGS[@]}"
            ;;
        distributed)
            exec "$ROOT_DIR/deployment/install_distributed.sh" \
                "${MODE_ARGS[@]}"
            ;;
        *)
            log_error "Unknown install mode: ${MODE}"
            usage
            exit 1
            ;;
    esac
}


main "$@"
