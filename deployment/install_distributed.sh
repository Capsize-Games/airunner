#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HELPERS="$ROOT_DIR/scripts/install_helpers.sh"

# shellcheck source=/dev/null
source "$HELPERS"

ROLE="daemon"
INSTALL_ROOT_BASE="${AIRUNNER_DISTRIBUTED_ROOT:-$HOME/.local/airunner/distributed}"
PYTHON_CMD="${AIRUNNER_DISTRIBUTED_PYTHON:-}"
TORCH_MODE="${AIRUNNER_DISTRIBUTED_TORCH:-auto}"
SERVICE_PROFILE=""
INSTALL_SYSTEMD=0
LOCAL_BIN_DIR="${HOME}/.local/bin"


usage() {
    cat <<EOF
Usage: ./deployment/install_distributed.sh [options]

Linux-first distributed installer for AIRunner daemon and GUI-client roles.

Options:
  --role ROLE                 daemon|gui-client
  --install-root PATH         Base install root for the selected role
  --python CMD                Python interpreter to use for venv creation
  --service-profile NAME      Services extra for the selected role
  --torch MODE                auto|cpu|cuda|skip
  --systemd                   Register the daemon role with systemd
  -h, --help                  Show this help text
EOF
}


parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --role)
                ROLE="$2"
                shift 2
                ;;
            --install-root)
                INSTALL_ROOT_BASE="$2"
                shift 2
                ;;
            --python)
                PYTHON_CMD="$2"
                shift 2
                ;;
            --service-profile)
                SERVICE_PROFILE="$2"
                shift 2
                ;;
            --torch)
                TORCH_MODE="$2"
                shift 2
                ;;
            --systemd)
                INSTALL_SYSTEMD=1
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown argument: $1"
                usage
                exit 1
                ;;
        esac
    done
}


normalize_role() {
    case "$ROLE" in
        daemon)
            printf 'daemon\n'
            ;;
        gui|gui-client)
            printf 'gui-client\n'
            ;;
        *)
            log_error "Unsupported distributed role: ${ROLE}"
            exit 1
            ;;
    esac
}


default_service_profile() {
    case "$1" in
        daemon)
            printf 'headless\n'
            ;;
        gui-client)
            printf 'core\n'
            ;;
    esac
}


role_install_root() {
    printf '%s/%s\n' "$INSTALL_ROOT_BASE" "$1"
}


install_packages() {
    local venv_python="$1"
    local role="$2"
    local service_profile="$3"

    case "$role" in
        daemon)
            "$venv_python" -m pip install \
                "$ROOT_DIR/services[$service_profile]" \
                "$ROOT_DIR/native"
            ;;
        gui-client)
            "$venv_python" -m pip install \
                "$ROOT_DIR/services[$service_profile]" \
                "$ROOT_DIR/native"
            ;;
    esac
}


link_role_command() {
    local role_root="$1"
    local role="$2"
    local source_path=""
    local target_name=""

    mkdir -p "$LOCAL_BIN_DIR"

    case "$role" in
        daemon)
            source_path="$role_root/venv/bin/airunner-daemon"
            target_name='airunner-distributed-daemon'
            ;;
        gui-client)
            source_path="$role_root/venv/bin/airunner"
            target_name='airunner-distributed-gui'
            ;;
    esac

    ln -sfn "$source_path" "$LOCAL_BIN_DIR/$target_name"
    log_success "Linked ${LOCAL_BIN_DIR}/${target_name}"
}


install_systemd_service() {
    local role_root="$1"
    local venv_python="$2"

    if [[ "$ROLE" != 'daemon' ]]; then
        log_error '--systemd is only supported for the daemon role'
        exit 1
    fi

    local installer="$ROOT_DIR/deployment/systemd/install.sh"
    local -a command=(
        env
        "AIRUNNER_TEMPLATE_ROOT=$ROOT_DIR"
        "AIRUNNER_INSTALL_ROOT=$role_root"
        "AIRUNNER_PYTHON=$venv_python"
        bash
        "$installer"
    )

    if [[ "$EUID" -ne 0 ]]; then
        sudo "${command[@]}"
        return
    fi

    "${command[@]}"
}


print_next_steps() {
    local role_root="$1"
    local role="$2"

    log_success 'Distributed install complete'
    printf 'Install root: %s\n' "$role_root"
    case "$role" in
        daemon)
            printf 'Launch manually: %s/venv/bin/airunner-daemon\n' "$role_root"
            printf 'Shortcut: %s/airunner-distributed-daemon\n' "$LOCAL_BIN_DIR"
            ;;
        gui-client)
            printf 'Launch manually: %s/venv/bin/airunner\n' "$role_root"
            printf 'Shortcut: %s/airunner-distributed-gui\n' "$LOCAL_BIN_DIR"
            ;;
    esac
}


main() {
    local resolved_role=""
    local resolved_python=""
    local role_root=""
    local service_profile=""
    local venv_python=""

    parse_args "$@"
    resolved_role="$(normalize_role)"
    ROLE="$resolved_role"
    role_root="$(role_install_root "$ROLE")"
    service_profile="${SERVICE_PROFILE:-$(default_service_profile "$ROLE") }"
    service_profile="${service_profile% }"

    resolved_python="$(find_python "$PYTHON_CMD" 3.13)" || {
        log_error 'Python 3.13+ is required for distributed installs'
        exit 1
    }
    log_success "Using Python: ${resolved_python}"

    mkdir -p "$role_root"
    venv_python="$(ensure_venv "$resolved_python" "$role_root/venv")"

    if service_extra_needs_torch "$service_profile"; then
        install_torch_stack "$venv_python" "$TORCH_MODE"
    fi

    log_info "Installing ${ROLE} packages with services[${service_profile}]"
    install_packages "$venv_python" "$ROLE" "$service_profile"
    link_role_command "$role_root" "$ROLE"

    if [[ "$INSTALL_SYSTEMD" == '1' ]]; then
        install_systemd_service "$role_root" "$venv_python"
    fi

    print_next_steps "$role_root" "$ROLE"
}


main "$@"