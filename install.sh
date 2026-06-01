#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${AIRUNNER_INSTALL_MODE:-single-package}"
INSTALL_DIR="${AIRUNNER_INSTALL_DIR:-$HOME/.local/airunner}"
BIN_DIR="${HOME}/.local/bin"
BUNDLE_ARCHIVE="${AIRUNNER_BUNDLE_ARCHIVE:-}"
XDG_DATA_HOME_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
DESKTOP_APPLICATIONS_DIR="${XDG_DATA_HOME_DIR}/applications"
ICON_INSTALL_DIR="${XDG_DATA_HOME_DIR}/icons/hicolor/64x64/apps"
REQUESTED_HELP=0
REQUESTED_UNINSTALL=0
MODE_ARGS=()


log_info() {
    printf '[INFO] %s\n' "$1"
}


log_success() {
    printf '[OK] %s\n' "$1"
}


log_error() {
    printf '[ERROR] %s\n' "$1" >&2
}


usage() {
    cat <<EOF
Usage: ./install.sh [options] [-- mode-specific args]

AIRunner now has three installer modes:
  single-package  Install a prebuilt bundle with embedded Python
  dev             Delegate to ./scripts/install.sh
  distributed     Delegate to ./deployment/install_distributed.sh

Options:
  --mode MODE                 single-package|dev|distributed
  --bundle-archive PATH       Bundle archive for single-package mode
  --install-dir PATH          Install root for single-package mode
  --uninstall                 Remove the single-package install
  -h, --help                  Show this help text
EOF
}


parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --mode)
                MODE="$2"
                shift 2
                ;;
            --bundle-archive)
                BUNDLE_ARCHIVE="$2"
                shift 2
                ;;
            --install-dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --uninstall|-u)
                REQUESTED_UNINSTALL=1
                shift
                ;;
            -h|--help)
                if [[ "$MODE" == 'single-package' ]]; then
                    REQUESTED_HELP=1
                else
                    MODE_ARGS+=("$1")
                fi
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


latest_local_bundle() {
    local latest=''
    latest="$(find "$ROOT_DIR/dist" -maxdepth 1 -type f \
        -name 'airunner-*-linux-*-bundle.tar.gz' | sort | tail -n 1)"
    printf '%s\n' "$latest"
}


dispatch_mode() {
    case "$MODE" in
        dev)
            exec "$ROOT_DIR/scripts/install.sh" "${MODE_ARGS[@]}"
            ;;
        distributed)
            exec "$ROOT_DIR/deployment/install_distributed.sh" \
                "${MODE_ARGS[@]}"
            ;;
        single-package)
            return 0
            ;;
        *)
            log_error "Unknown install mode: ${MODE}"
            exit 1
            ;;
    esac
}


extract_bundle_root() {
    local archive_path="$1"
    local extract_root="$2"
    local entries

    mkdir -p "$extract_root"
    tar -xzf "$archive_path" -C "$extract_root"
    entries=("$extract_root"/*)

    if [[ ${#entries[@]} -eq 1 && -d "${entries[0]}" ]]; then
        printf '%s\n' "${entries[0]}"
        return
    fi

    printf '%s\n' "$extract_root"
}


install_desktop_assets() {
    local desktop_source="$INSTALL_DIR/share/applications/airunner.desktop"
    local icon_source="$INSTALL_DIR/share/icons/hicolor/64x64/apps/airunner.png"

    if [[ -f "$desktop_source" ]]; then
        mkdir -p "$DESKTOP_APPLICATIONS_DIR"
        cp "$desktop_source" "$DESKTOP_APPLICATIONS_DIR/airunner.desktop"
    fi

    if [[ -f "$icon_source" ]]; then
        mkdir -p "$ICON_INSTALL_DIR"
        cp "$icon_source" "$ICON_INSTALL_DIR/airunner.png"
    fi
}


install_headless_wrapper() {
    mkdir -p "$BIN_DIR"
    cat > "$BIN_DIR/airunner-headless" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/bin/airunner" --headless "\$@"
EOF
    chmod +x "$BIN_DIR/airunner-headless"
}


install_single_package() {
    local archive_path="$BUNDLE_ARCHIVE"
    local temp_root=''
    local extracted_root=''

    if [[ -z "$archive_path" ]]; then
        archive_path="$(latest_local_bundle)"
    fi

    if [[ -z "$archive_path" || ! -f "$archive_path" ]]; then
        log_error 'single-package mode requires a prebuilt bundle archive'
        log_error 'Pass --bundle-archive or stage one under ./dist first'
        exit 1
    fi

    log_info "Installing bundle from ${archive_path}"
    temp_root="$(mktemp -d)"
    extracted_root="$(extract_bundle_root "$archive_path" "$temp_root")"

    rm -rf "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR" "$BIN_DIR"
    cp -a "$extracted_root"/. "$INSTALL_DIR/"
    rm -rf "$temp_root"

    if [[ ! -x "$INSTALL_DIR/bin/airunner" ]]; then
        log_error "Installed bundle is missing ${INSTALL_DIR}/bin/airunner"
        exit 1
    fi

    ln -sfn "$INSTALL_DIR/bin/airunner" "$BIN_DIR/airunner"
    install_headless_wrapper
    install_desktop_assets

    log_success 'Single-package install complete'
    printf 'Launcher: %s/airunner\n' "$BIN_DIR"
}


uninstall_single_package() {
    rm -rf "$INSTALL_DIR"
    rm -f "$BIN_DIR/airunner" "$BIN_DIR/airunner-headless"
    rm -f "$DESKTOP_APPLICATIONS_DIR/airunner.desktop"
    rm -f "$ICON_INSTALL_DIR/airunner.png"
    log_success 'Single-package install removed'
}


main() {
    parse_args "$@"

    if [[ "$REQUESTED_HELP" == '1' ]]; then
        usage
        return
    fi

    dispatch_mode

    if [[ "$REQUESTED_UNINSTALL" == '1' ]]; then
        uninstall_single_package
        return
    fi

    install_single_package
}


main "$@"
