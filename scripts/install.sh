#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HELPERS="$ROOT_DIR/scripts/install_helpers.sh"

# shellcheck source=/dev/null
source "$HELPERS"

VENV_DIR="${AIRUNNER_DEV_VENV:-$ROOT_DIR/venv}"
PYTHON_CMD="${AIRUNNER_DEV_PYTHON:-}"
SERVICE_PROFILE="${AIRUNNER_DEV_SERVICE_PROFILE:-linux-release}"
TORCH_MODE="${AIRUNNER_DEV_TORCH:-auto}"
SIDECAR_MODE="${AIRUNNER_DEV_SIDECARS:-auto}"
SIDECAR_ENABLE_CUDA="${AIRUNNER_DEV_SIDECAR_CUDA:-0}"
SIDECAR_CLEAN=0
REFRESH_DEPS=0
WITH_DEV_TOOLS=1


usage() {
	cat <<EOF
Usage: ./scripts/install.sh [options]

Canonical developer installer for editable AIRunner worktrees.

Options:
  --venv PATH                Virtual environment path
  --python CMD               Python interpreter to use for venv creation
  --service-profile NAME     Services extra to install editably
  --torch MODE               auto|cpu|cuda|skip
	--sidecars MODE            auto|always|skip
	--sidecars-cuda            Stage the verified CUDA profile alongside CPU sidecars
	--clean-sidecars           Allow replacing an owned tree that contains CUDA
	--refresh-deps             Re-resolve Python dependencies in an existing venv
  --without-dev-tools        Omit the development extra from services
  -h, --help                 Show this help text
EOF
}


parse_args() {
	while [[ $# -gt 0 ]]; do
		case "$1" in
			--venv)
				VENV_DIR="$2"
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
			--sidecars)
				SIDECAR_MODE="$2"
				shift 2
				;;
			--sidecars-cuda)
				SIDECAR_ENABLE_CUDA=1
				shift
				;;
			--clean-sidecars)
				SIDECAR_CLEAN=1
				shift
				;;
			--refresh-deps)
				REFRESH_DEPS=1
				shift
				;;
			--without-dev-tools)
				WITH_DEV_TOOLS=0
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


service_extras() {
	local extras="$SERVICE_PROFILE"
	if [[ "$WITH_DEV_TOOLS" == "1" ]]; then
		extras="${extras},development"
	fi
	printf '%s\n' "$extras"
}


install_editable_packages() {
	local venv_python="$1"
	local extras="$2"
	local install_mode="$3"
	local -a pip_args=(install)

	if [[ "$install_mode" == 'editable-only' ]]; then
		pip_args+=(--no-deps)
	fi

	"$venv_python" -m pip "${pip_args[@]}" \
		-e "$ROOT_DIR/services[$extras]" \
		-e "$ROOT_DIR/native"
}


sidecars_requested() {
	local extras="$1"

	case "$SIDECAR_MODE" in
		auto)
			service_extra_needs_sidecars "$extras"
			return
			;;
		always)
			return 0
			;;
		skip)
			return 1
			;;
		*)
			log_error "Unknown sidecar mode: ${SIDECAR_MODE}"
			exit 1
			;;
	esac
}


NATIVE_RUNTIME_DIR="$ROOT_DIR/build/runtime-sidecars/linux"
NATIVE_CUDA_PROFILE_PIN="${AIRUNNER_NATIVE_CUDA_PROFILE_PIN:-$ROOT_DIR/.github/native-cuda-profile-pin.json}"

link_sidecar_binaries() {
	local bin_dir="$1"
	local venv_bin_dir="$2"
	local binary_name=""

	# Validate the whole verified payload before replacing either link.
	for binary_name in llama-server whisper-server; do
		if [[ ! -x "$bin_dir/$binary_name" ]]; then
			log_error "Missing sidecar binary: ${bin_dir}/${binary_name}"
			exit 1
		fi
		if [[ -d "$venv_bin_dir/$binary_name" && ! -L "$venv_bin_dir/$binary_name" ]]; then
			log_error "Sidecar destination is a directory: ${venv_bin_dir}/${binary_name}"
			exit 1
		fi
	done
	for binary_name in llama-server whisper-server; do
		ln -sfnT "$bin_dir/$binary_name" "$venv_bin_dir/$binary_name"
	done
}

# Fetch the pinned CPU payload and optionally its separately pinned CUDA profile.
stage_prebuilt_native_runtime() {
	local venv_python="$1"
	local venv_bin_dir
	venv_bin_dir="$(dirname "$venv_python")"
	local -a stage_args=(--fetch --output-dir "$NATIVE_RUNTIME_DIR" --replace-existing)
	if [[ "$SIDECAR_ENABLE_CUDA" == '1' ]]; then
		stage_args+=(--cuda-profile-pin "$NATIVE_CUDA_PROFILE_PIN" --require-cuda-profile)
		log_info 'Fetching the separately pinned CPU sidecars and verified CUDA profile'
	else
		log_info 'Fetching the pinned CPU sidecar bundle with notices and provenance'
	fi
	if [[ "$SIDECAR_CLEAN" == '1' ]]; then
		stage_args+=(--clean-existing)
	fi
	mkdir -p "$(dirname "$NATIVE_RUNTIME_DIR")"
	if ! python3 "$ROOT_DIR/scripts/stage_native_runtime_payload.py" "${stage_args[@]}"; then
		log_error 'Native runtime payload staging failed; installed sidecar links were not changed'
		exit 1
	fi
	link_sidecar_binaries "$NATIVE_RUNTIME_DIR/bin" "$venv_bin_dir"
	log_success "Linked CPU sidecars from the staged native runtime into ${venv_bin_dir}"
}

install_runtime_sidecars() {
	local venv_python="$1"

	if [[ "$(uname -s)" != 'Linux' ]]; then
		log_warning 'Skipping native runtime sidecars on a non-Linux host'
		return 0
	fi

	stage_prebuilt_native_runtime "$venv_python"
}


main() {
	local resolved_python=""
	local venv_python=""
	local extras=""
	local install_mode='resolved'
	local venv_exists=0

	if [[ -x "$VENV_DIR/bin/python" ]]; then
		venv_exists=1
	fi

	parse_args "$@"
	if [[ "$SIDECAR_ENABLE_CUDA" == '1' && "$SIDECAR_MODE" == 'skip' ]]; then
		log_error '--sidecars-cuda cannot be combined with --sidecars skip'
		exit 1
	fi

	if service_profile_uses_deferred_tts_vendor "$SERVICE_PROFILE"; then
		log_error "Service profile '${SERVICE_PROFILE}' includes deferred airunner-tts-vendor; use linux-release or tts-python-core while OpenVoice/Melo remain deferred"
		exit 1
	fi

	resolved_python="$(find_python "$PYTHON_CMD" 3.13)" || {
		log_error 'Python 3.13+ is required for development installs'
		exit 1
	}
	log_success "Using Python: ${resolved_python}"

	venv_python="$(ensure_venv "$resolved_python" "$VENV_DIR")"
	extras="$(service_extras)"

	if service_extra_needs_torch "$extras"; then
		install_torch_stack "$venv_python" "$TORCH_MODE"
	fi

	if [[ "$venv_exists" == '1' && "$REFRESH_DEPS" != '1' ]]; then
		install_mode='editable-only'
		log_info 'Existing venv detected; refreshing editable installs only'
	else
		log_info "Installing editable packages with services[${extras}]"
	fi
	install_editable_packages "$venv_python" "$extras" "$install_mode"

	if sidecars_requested "$extras"; then
		install_runtime_sidecars "$venv_python"
	else
		log_info 'Skipping native runtime sidecars'
	fi

	log_success 'Developer install complete'
	printf 'Activate with: source %s/bin/activate\n' "$VENV_DIR"
}


main "$@"
