#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_PLATFORM="linux"
BUNDLE_NAME="desktop"
INSTALL_EXTRA=""
OUTPUT_ROOT="$ROOT_DIR/build/end-user-bundles"
DIST_ROOT="$ROOT_DIR/dist"
WORK_ROOT="$ROOT_DIR/build/end-user-bundle-work"
CLEAN=0
DRY_RUN=0

usage() {
    cat <<'EOF'
Usage: ./scripts/build_airunner_bundle.sh [options]

Options:
  --target-platform linux|windows  Build a Linux or Windows bundle
  --bundle-name NAME               Bundle variant name (default: desktop)
  --install-extra EXTRA            Override the AIRunner install extra
  --output-root PATH               Staged bundle output root
  --dist-root PATH                 Archive output root
  --work-root PATH                 Download and extraction work root
  --clean                          Remove previous bundle output first
  --dry-run                        Print commands without executing them
  -h, --help                       Show this help text
EOF
}

run_cmd() {
    echo "+ $*"
    if [[ "$DRY_RUN" == "1" ]]; then
        return 0
    fi
    "$@"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --target-platform)
                TARGET_PLATFORM="$2"
                shift 2
                ;;
            --bundle-name)
                BUNDLE_NAME="$2"
                shift 2
                ;;
            --install-extra)
                INSTALL_EXTRA="$2"
                shift 2
                ;;
            --output-root)
                OUTPUT_ROOT="$2"
                shift 2
                ;;
            --dist-root)
                DIST_ROOT="$2"
                shift 2
                ;;
            --work-root)
                WORK_ROOT="$2"
                shift 2
                ;;
            --clean)
                CLEAN=1
                shift
                ;;
            --dry-run)
                DRY_RUN=1
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1" >&2
                usage >&2
                exit 1
                ;;
        esac
    done
}

launcher_binary() {
    case "$TARGET_PLATFORM" in
        linux)
            echo "$ROOT_DIR/build/airunner-launcher/airunner"
            ;;
        windows)
            echo "$ROOT_DIR/build/airunner-launcher-windows/airunner.exe"
            ;;
    esac
}

sidecar_root() {
    echo "$ROOT_DIR/build/runtime-sidecars/$TARGET_PLATFORM"
}

ensure_launcher() {
    local -a args
    local binary
    binary="$(launcher_binary)"
    if [[ "$CLEAN" != "1" && -f "$binary" ]]; then
        return
    fi
    args=(
        "$ROOT_DIR/scripts/build_airunner_launcher.sh"
        --target-platform "$TARGET_PLATFORM"
    )
    if [[ "$CLEAN" == "1" ]]; then
        args+=(--clean)
    fi
    run_cmd "${args[@]}"
}

ensure_sidecars() {
    local -a args
    local root
    root="$(sidecar_root)"
    if [[ "$CLEAN" != "1" && -d "$root" ]]; then
        return
    fi
    args=(
        "$ROOT_DIR/scripts/build_runtime_sidecars.sh"
        --target-platform "$TARGET_PLATFORM"
    )
    if [[ "$CLEAN" == "1" ]]; then
        args+=(--clean)
    fi
    run_cmd "${args[@]}"
}

python_command() {
    if [[ -x "$ROOT_DIR/venv/bin/python" ]]; then
        echo "$ROOT_DIR/venv/bin/python"
        return
    fi
    echo "python3"
}

main() {
    parse_args "$@"
    ensure_launcher
    ensure_sidecars

    local -a cmd
    local python_path
    cmd=(
        "$(python_command)"
        -m
        airunner_native.bin.build_end_user_bundle
        --target-platform "$TARGET_PLATFORM"
        --bundle-name "$BUNDLE_NAME"
        --launcher-binary "$(launcher_binary)"
        --sidecar-root "$(sidecar_root)"
        --output-root "$OUTPUT_ROOT"
        --dist-root "$DIST_ROOT"
        --work-root "$WORK_ROOT"
    )

    if [[ -n "$INSTALL_EXTRA" ]]; then
        cmd+=(--install-extra "$INSTALL_EXTRA")
    fi
    if [[ "$CLEAN" == "1" ]]; then
        cmd+=(--clean)
    fi
    if [[ "$DRY_RUN" == "1" ]]; then
        cmd+=(--dry-run)
    fi

    python_path="$ROOT_DIR/native/src${PYTHONPATH:+:$PYTHONPATH}"
    run_cmd env "PYTHONPATH=$python_path" "${cmd[@]}"
}

main "$@"