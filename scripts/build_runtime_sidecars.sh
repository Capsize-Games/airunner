#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PINS_FILE="$ROOT_DIR/native/runtime_sidecars/runtime_pins.env"

TARGET_PLATFORM="linux"
OUTPUT_ROOT="$ROOT_DIR/build/runtime-sidecars"
WORK_ROOT="$ROOT_DIR/build/runtime-sidecars-work"
CMAKE_BUILD_TYPE="Release"
JOBS="${AIRUNNER_BUILD_JOBS:-}"
CLEAN=0
DRY_RUN=0

CMAKE_PLATFORM_ARGS=()
BINARY_SUFFIX=""

usage() {
    cat <<'EOF'
Usage: ./scripts/build_runtime_sidecars.sh [options]

Options:
  --target-platform linux|windows  Build native or Windows sidecars
  --output-root PATH               Bundle output root directory
  --work-root PATH                 Source and build work directory
  --clean                          Remove previous output for the target
  --dry-run                        Print build steps without running them
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
            --output-root)
                OUTPUT_ROOT="$2"
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

load_pins() {
    # shellcheck disable=SC1090
    source "$PINS_FILE"
}

detect_jobs() {
    if [[ -n "$JOBS" ]]; then
        echo "$JOBS"
        return
    fi
    if command -v nproc >/dev/null 2>&1; then
        nproc
        return
    fi
    echo 4
}

configure_platform() {
    CMAKE_PLATFORM_ARGS=()
    BINARY_SUFFIX=""

    if [[ "$TARGET_PLATFORM" == "linux" ]]; then
        return
    fi

    if [[ "$TARGET_PLATFORM" != "windows" ]]; then
        echo "Unsupported target platform: $TARGET_PLATFORM" >&2
        exit 1
    fi

    local cxx
    local cc
    cxx="$(command -v x86_64-w64-mingw32-g++-posix || true)"
    if [[ -z "$cxx" ]]; then
        cxx="$(command -v x86_64-w64-mingw32-g++ || true)"
    fi
    cc="$(command -v x86_64-w64-mingw32-gcc-posix || true)"
    if [[ -z "$cc" ]]; then
        cc="$(command -v x86_64-w64-mingw32-gcc || true)"
    fi
    if [[ -z "$cxx" || -z "$cc" ]]; then
        echo "MinGW-w64 is required for Windows sidecar builds" >&2
        exit 1
    fi

    CMAKE_PLATFORM_ARGS=(
        -DCMAKE_SYSTEM_NAME=Windows
        -DCMAKE_C_COMPILER="$cc"
        -DCMAKE_CXX_COMPILER="$cxx"
    )
    BINARY_SUFFIX=".exe"
}

clean_target() {
    if [[ "$CLEAN" != "1" ]]; then
        return
    fi
    run_cmd rm -rf \
        "$OUTPUT_ROOT/$TARGET_PLATFORM" \
        "$WORK_ROOT/$TARGET_PLATFORM"
}

prepare_layout() {
    BUNDLE_ROOT="$OUTPUT_ROOT/$TARGET_PLATFORM"
    BUNDLE_BIN_DIR="$BUNDLE_ROOT/bin"
    BUNDLE_SHARE_DIR="$BUNDLE_ROOT/share/airunner"
    SOURCE_DIR="$WORK_ROOT/$TARGET_PLATFORM/src"
    BUILD_DIR="$WORK_ROOT/$TARGET_PLATFORM/build"

    run_cmd mkdir -p \
        "$BUNDLE_BIN_DIR" \
        "$BUNDLE_SHARE_DIR" \
        "$SOURCE_DIR" \
        "$BUILD_DIR"
}

fetch_repo() {
    local name="$1"
    local repository="$2"
    local commit="$3"
    local destination="$SOURCE_DIR/$name"

    if [[ ! -d "$destination/.git" ]]; then
        run_cmd git clone --filter=blob:none "$repository" "$destination"
    fi

    run_cmd git -C "$destination" fetch --depth 1 origin "$commit"
    run_cmd git -C "$destination" checkout --detach "$commit"
}

configure_build() {
    local source_path="$1"
    local build_path="$2"
    shift 2

    run_cmd cmake \
        -S "$source_path" \
        -B "$build_path" \
        -DCMAKE_BUILD_TYPE="$CMAKE_BUILD_TYPE" \
        -DBUILD_SHARED_LIBS=OFF \
        "${CMAKE_PLATFORM_ARGS[@]}" \
        "$@"
}

build_target() {
    local build_path="$1"
    local target_name="$2"
    local jobs
    jobs="$(detect_jobs)"

    run_cmd cmake \
        --build "$build_path" \
        --config "$CMAKE_BUILD_TYPE" \
        --target "$target_name" \
        --parallel "$jobs"
}

copy_binary() {
    local build_path="$1"
    local binary_name="$2"
    local source_binary="$build_path/bin/${binary_name}${BINARY_SUFFIX}"
    local destination_binary="$BUNDLE_BIN_DIR/${binary_name}${BINARY_SUFFIX}"

    if [[ "$DRY_RUN" != "1" && ! -f "$source_binary" ]]; then
        echo "Expected binary was not produced: $source_binary" >&2
        exit 1
    fi

    run_cmd cp "$source_binary" "$destination_binary"
}

write_manifest() {
    local manifest_path="$BUNDLE_SHARE_DIR/runtime_manifest.env"
    local pins_path="$BUNDLE_SHARE_DIR/runtime_pins.env"

    if [[ "$DRY_RUN" == "1" ]]; then
        echo "+ write $manifest_path"
        echo "+ copy $PINS_FILE $pins_path"
        return
    fi

    cat > "$manifest_path" <<EOF
# Generated by scripts/build_runtime_sidecars.sh.
AIRUNNER_BUNDLE_ROOT=../..
AIRUNNER_PYTHON=../../python/bin/python
AIRUNNER_PYTHONPATH=../../app/site-packages
AIRUNNER_ENTRYPOINT=airunner.launcher
AIRUNNER_LLAMA_SERVER_BIN=../../bin/llama-server${BINARY_SUFFIX}
AIRUNNER_WHISPER_SERVER_BIN=../../bin/whisper-server${BINARY_SUFFIX}
EOF

    cp "$PINS_FILE" "$pins_path"
}

build_llama_sidecar() {
    local source_path="$SOURCE_DIR/llama.cpp"
    local build_path="$BUILD_DIR/llama.cpp"

    fetch_repo \
        "llama.cpp" \
        "$LLAMA_CPP_REPOSITORY" \
        "$LLAMA_CPP_COMMIT"
    configure_build \
        "$source_path" \
        "$build_path" \
        -DLLAMA_BUILD_SERVER=ON \
        -DLLAMA_BUILD_TESTS=OFF \
        -DLLAMA_BUILD_TOOLS=ON \
        -DLLAMA_BUILD_WEBUI=OFF
    build_target "$build_path" "llama-server"
    copy_binary "$build_path" "llama-server"
}

build_whisper_sidecar() {
    local source_path="$SOURCE_DIR/whisper.cpp"
    local build_path="$BUILD_DIR/whisper.cpp"

    fetch_repo \
        "whisper.cpp" \
        "$WHISPER_CPP_REPOSITORY" \
        "$WHISPER_CPP_COMMIT"
    configure_build \
        "$source_path" \
        "$build_path" \
        -DWHISPER_BUILD_SERVER=ON \
        -DWHISPER_BUILD_TESTS=OFF \
        -DWHISPER_SDL2=OFF
    build_target "$build_path" "whisper-server"
    copy_binary "$build_path" "whisper-server"
}

main() {
    parse_args "$@"
    load_pins
    configure_platform
    clean_target
    prepare_layout
    build_llama_sidecar
    build_whisper_sidecar
    write_manifest

    echo
    echo "Built native runtime sidecars in: $OUTPUT_ROOT/$TARGET_PLATFORM"
}

main "$@"