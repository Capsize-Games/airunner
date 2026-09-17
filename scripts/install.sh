#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HELPERS="$ROOT_DIR/scripts/install_helpers.sh"

# shellcheck source=/dev/null
source "$HELPERS"

VENV_DIR="${AIRUNNER_DEV_VENV:-$ROOT_DIR/venv}"
PYTHON_CMD="${AIRUNNER_DEV_PYTHON:-}"
SERVICE_PROFILE="${AIRUNNER_DEV_SERVICE_PROFILE:-desktop}"
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
	--sidecars-cuda            Build llama.cpp and whisper.cpp with CUDA
	--clean-sidecars           Rebuild native sidecars from scratch
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
		-e "$ROOT_DIR/native" \
		-e "$ROOT_DIR"
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


NATIVE_SIDECAR_REPO='Capsize-Games/airunner-native'
NATIVE_SIDECAR_VERSION_FILE="$ROOT_DIR/.github/native-sidecar-version"

native_sidecar_tag() {
	if [[ ! -f "$NATIVE_SIDECAR_VERSION_FILE" ]]; then
		log_error "Missing pin file: ${NATIVE_SIDECAR_VERSION_FILE}"
		exit 1
	fi
	<"$NATIVE_SIDECAR_VERSION_FILE" tr -d '[:space:]'
}

link_sidecar_binaries() {
	local bin_dir="$1"
	local venv_bin_dir="$2"
	local binary_name=""

	for binary_name in llama-server whisper-server; do
		if [[ ! -x "$bin_dir/$binary_name" ]]; then
			log_error "Missing sidecar binary: ${bin_dir}/${binary_name}"
			exit 1
		fi
		ln -sfn "$bin_dir/$binary_name" "$venv_bin_dir/$binary_name"
	done
}

# The common case: download the prebuilt bundle the pinned
# airunner-native release publishes, rather than needing
# cmake/mingw-w64/ninja on every dev machine (the sidecar build itself
# now lives in that repository -- see
# https://github.com/Capsize-Games/airunner-native).
fetch_prebuilt_sidecars() {
	local venv_python="$1"
	local venv_bin_dir="$(dirname "$venv_python")"
	local tag download_dir archive_path

	tag="$(native_sidecar_tag)"
	download_dir="$ROOT_DIR/build/runtime-sidecars-download"
	archive_path="$download_dir/runtime-sidecars-linux.tar.gz"

	if [[ "$SIDECAR_CLEAN" == '1' ]]; then
		rm -rf "$download_dir"
	fi
	mkdir -p "$download_dir"

	log_info "Downloading prebuilt native sidecars (${tag}) from ${NATIVE_SIDECAR_REPO}"
	if ! curl -fsSL \
		"https://github.com/${NATIVE_SIDECAR_REPO}/releases/download/${tag}/runtime-sidecars-linux.tar.gz" \
		-o "$archive_path"; then
		log_error "Failed to download sidecar bundle for ${tag}"
		exit 1
	fi
	tar -xzf "$archive_path" -C "$download_dir"

	link_sidecar_binaries "$download_dir/bin" "$venv_bin_dir"
	log_success "Linked prebuilt native sidecars into ${venv_bin_dir}"
}

# CUDA builds aren't part of the published bundle (CI builds the
# linux/windows matrix without a CUDA runner), so --sidecars-cuda
# clones the pinned tag and builds from source instead.
build_sidecars_from_source() {
	local venv_python="$1"
	local venv_bin_dir="$(dirname "$venv_python")"
	local tag clone_dir
	local -a builder_args=(--target-platform linux)

	tag="$(native_sidecar_tag)"
	clone_dir="$ROOT_DIR/build/airunner-native-src"

	if [[ "$SIDECAR_CLEAN" == '1' || ! -d "$clone_dir" ]]; then
		rm -rf "$clone_dir"
		log_info "Cloning airunner-native (${tag}) for a CUDA sidecar build"
		git clone --quiet --depth 1 --branch "$tag" \
			"https://github.com/${NATIVE_SIDECAR_REPO}.git" "$clone_dir"
	fi

	if [[ "$SIDECAR_CLEAN" == '1' ]]; then
		builder_args+=(--clean)
	fi
	builder_args+=(--enable-cuda)

	log_info 'Building native llama.cpp and whisper.cpp sidecars from source (CUDA)'
	"$clone_dir/scripts/build_runtime_sidecars.sh" "${builder_args[@]}"

	link_sidecar_binaries \
		"$clone_dir/build/runtime-sidecars/linux/bin" \
		"$venv_bin_dir"
	log_success "Linked source-built native sidecars into ${venv_bin_dir}"
}

install_runtime_sidecars() {
	local venv_python="$1"

	if [[ "$(uname -s)" != 'Linux' ]]; then
		log_warning 'Skipping native runtime sidecars on a non-Linux host'
		return 0
	fi

	if [[ "$SIDECAR_ENABLE_CUDA" == '1' ]]; then
		build_sidecars_from_source "$venv_python"
	else
		fetch_prebuilt_sidecars "$venv_python"
	fi
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
