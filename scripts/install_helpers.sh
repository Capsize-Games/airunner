#!/usr/bin/env bash

command_exists() {
    command -v "$1" >/dev/null 2>&1
}


log_info() {
    printf '[INFO] %s\n' "$1"
}


log_success() {
    printf '[OK] %s\n' "$1"
}


log_warning() {
    printf '[WARN] %s\n' "$1"
}


log_error() {
    printf '[ERROR] %s\n' "$1" >&2
}


version_ge() {
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}


get_python_version() {
    "$1" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' \
        2>/dev/null
}


find_python() {
    local requested_python="${1:-}"
    local min_version="${2:-3.13}"
    local candidate=""
    local version=""

    if [[ -n "$requested_python" ]]; then
        if ! command_exists "$requested_python" && [[ ! -x "$requested_python" ]]; then
            return 1
        fi
        version="$(get_python_version "$requested_python")"
        if [[ -n "$version" ]] && version_ge "$version" "$min_version"; then
            printf '%s\n' "$requested_python"
            return 0
        fi
        return 1
    fi

    for candidate in python3.13 python3 python; do
        if ! command_exists "$candidate"; then
            continue
        fi
        version="$(get_python_version "$candidate")"
        if [[ -n "$version" ]] && version_ge "$version" "$min_version"; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    return 1
}


ensure_venv() {
    local python_cmd="$1"
    local venv_dir="$2"
    local venv_python="${venv_dir}/bin/python"

    if [[ ! -d "$venv_dir" ]]; then
        printf '[INFO] Creating virtual environment at %s\n' "$venv_dir" >&2
        "$python_cmd" -m venv "$venv_dir"
    else
        printf '[INFO] Reusing virtual environment at %s\n' "$venv_dir" >&2
    fi

    "$venv_python" -m pip install --upgrade pip 'setuptools<82' wheel >/dev/null
    printf '%s\n' "$venv_python"
}


service_extra_needs_torch() {
    case ",${1}," in
        *,llm-native,*|*,art-python,*|*,tts-python,*|*,headless,*|*,desktop,*|*,all,*|*,all_dev,*|*,all_native,*|*,all_dev_native,*)
            return 0
            ;;
    esac
    return 1
}


service_extra_needs_sidecars() {
    case ",${1}," in
        *,llm-native,*|*,stt-native,*|*,llm,*|*,headless,*|*,desktop,*|*,all,*|*,all_dev,*|*,all_native,*|*,all_dev_native,*)
            return 0
            ;;
    esac
    return 1
}


install_torch_stack() {
    local python_bin="$1"
    local torch_mode="$2"
    local index_url=""

    case "$torch_mode" in
        skip)
            log_info 'Skipping torch installation'
            return 0
            ;;
        auto)
            if command_exists nvidia-smi; then
                index_url='https://download.pytorch.org/whl/cu128'
                log_info 'Installing torch with CUDA wheels'
            else
                index_url='https://download.pytorch.org/whl/cpu'
                log_info 'Installing torch with CPU wheels'
            fi
            ;;
        cuda)
            index_url='https://download.pytorch.org/whl/cu128'
            log_info 'Installing torch with CUDA wheels'
            ;;
        cpu)
            index_url='https://download.pytorch.org/whl/cpu'
            log_info 'Installing torch with CPU wheels'
            ;;
        *)
            log_error "Unknown torch mode: ${torch_mode}"
            return 1
            ;;
    esac

    "$python_bin" -m pip install \
        torch torchvision torchaudio \
        --index-url "$index_url"
}