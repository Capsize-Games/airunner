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

    "$venv_python" -m pip install --upgrade pip setuptools wheel >/dev/null
    printf '%s\n' "$venv_python"
}


# Pinned torch stack (release issues #2432/#2433). These MUST match
# services/setup.py ML_RUNTIME_REQUIREMENTS, plus the torchcodec pin in
# the release lock (package/constraints-linux-nvidia-cu129.txt):
# services[headless] demands torch==2.13.0+cu129, so installing any
# other build here just forces a later reinstall (or a broken mix of a
# wrong-CUDA or CPU torch under cu129-built bitsandbytes/torchcodec).
AIRUNNER_TORCH_VERSION='2.13.0+cu129'
AIRUNNER_TORCHVISION_VERSION='0.28.0+cu129'
AIRUNNER_TORCHAUDIO_VERSION='2.11.0+cu129'
AIRUNNER_TORCHCODEC_VERSION='0.9.1'
AIRUNNER_TORCH_CUDA_INDEX='https://download.pytorch.org/whl/cu129'
AIRUNNER_TORCH_CPU_INDEX='https://download.pytorch.org/whl/cpu'


service_extra_needs_torch() {
    case ",${1}," in
        *,llm,*|*,llm-native,*|*,art-python,*|*,tts-python,*|*,headless,*|*,desktop,*|*,windows,*|*,all,*|*,all_dev,*|*,all_native,*|*,all_dev_native,*)
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


torch_version_matches() {
    local python_bin="$1"
    local expected_version="$2"
    local installed_version=""

    installed_version="$(
        "$python_bin" -c 'import torch; print(torch.__version__)' \
            2>/dev/null
    )" || return 1
    [[ "$installed_version" == "$expected_version" ]]
}


install_cuda_torch_stack() {
    local python_bin="$1"

    log_info 'Installing pinned torch with CUDA wheels'
    "$python_bin" -m pip install --force-reinstall \
        "torch==${AIRUNNER_TORCH_VERSION}" \
        "torchvision==${AIRUNNER_TORCHVISION_VERSION}" \
        "torchaudio==${AIRUNNER_TORCHAUDIO_VERSION}" \
        "torchcodec==${AIRUNNER_TORCHCODEC_VERSION}" \
        --index-url "$AIRUNNER_TORCH_CUDA_INDEX"
}


install_cpu_torch_stack() {
    local python_bin="$1"

    log_info 'Installing pinned torch with CPU wheels (dev fallback only)'
    "$python_bin" -m pip install --force-reinstall \
        "torch==${AIRUNNER_TORCH_VERSION%%+*}" \
        "torchvision==${AIRUNNER_TORCHVISION_VERSION%%+*}" \
        "torchaudio==${AIRUNNER_TORCHAUDIO_VERSION%%+*}" \
        "torchcodec==${AIRUNNER_TORCHCODEC_VERSION}" \
        --index-url "$AIRUNNER_TORCH_CPU_INDEX" \
        --extra-index-url https://pypi.org/simple
}


install_torch_stack() {
    local python_bin="$1"
    local torch_mode="$2"

    case "$torch_mode" in
        skip)
            log_info 'Skipping torch installation'
            return 0
            ;;
        auto)
            if torch_version_matches \
                "$python_bin" "$AIRUNNER_TORCH_VERSION"; then
                log_info "torch ${AIRUNNER_TORCH_VERSION} already installed"
                return 0
            fi
            if "$python_bin" -c 'import torch' >/dev/null 2>&1; then
                log_info 'Installed torch mismatches the pinned release line'
                log_info 'Reinstalling the pinned torch stack'
            fi
            if command_exists nvidia-smi; then
                install_cuda_torch_stack "$python_bin"
            else
                install_cpu_torch_stack "$python_bin"
            fi
            return 0
            ;;
        cuda)
            install_cuda_torch_stack "$python_bin"
            ;;
        cpu)
            install_cpu_torch_stack "$python_bin"
            ;;
        *)
            log_error "Unknown torch mode: ${torch_mode}"
            return 1
            ;;
    esac
}