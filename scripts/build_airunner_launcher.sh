#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_TYPE="${CMAKE_BUILD_TYPE:-RelWithDebInfo}"
TARGET_PLATFORM="linux"
STAMP_FILE_NAME=".airunner-launcher-build-stamp"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-platform)
      TARGET_PLATFORM="$2"
      shift 2
      ;;
    --clean)
      CLEAN_BUILD=1
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

CLEAN_BUILD="${CLEAN_BUILD:-0}"

case "${TARGET_PLATFORM}" in
  linux)
    BUILD_DIR="${ROOT_DIR}/build/airunner-launcher"
    OUTPUT_NAME="airunner"
    ;;
  windows)
    BUILD_DIR="${ROOT_DIR}/build/airunner-launcher-windows"
    OUTPUT_NAME="airunner.exe"
    ;;
  *)
    echo "Unsupported target platform: ${TARGET_PLATFORM}" >&2
    exit 1
    ;;
esac

if [[ "${CLEAN_BUILD}" == "1" ]]; then
  rm -rf "${BUILD_DIR}"
fi

cmake_args=(
  -S "${ROOT_DIR}/native/airunner_launcher"
  -B "${BUILD_DIR}"
  -DCMAKE_BUILD_TYPE="${BUILD_TYPE}"
)

if [[ "${TARGET_PLATFORM}" == "windows" ]]; then
  WIN_CXX="$(command -v x86_64-w64-mingw32-g++-posix || command -v x86_64-w64-mingw32-g++ || true)"
  if [[ -z "${WIN_CXX}" ]]; then
    echo "No MinGW-w64 C++ compiler found for Windows target" >&2
    exit 1
  fi
  cmake_args+=(
    -DCMAKE_SYSTEM_NAME=Windows
    -DCMAKE_CXX_COMPILER="${WIN_CXX}"
  )
fi

if [[ -n "${CMAKE_GENERATOR:-}" ]]; then
  cmake_args+=( -G "${CMAKE_GENERATOR}" )
elif command -v ninja >/dev/null 2>&1; then
  cmake_args+=( -G Ninja )
fi

cmake "${cmake_args[@]}"
cmake --build "${BUILD_DIR}" --config "${BUILD_TYPE}"

STAMP_FILE="${BUILD_DIR}/${STAMP_FILE_NAME}"
CURRENT_HEAD=""
if git -C "${ROOT_DIR}" rev-parse HEAD >/dev/null 2>&1; then
  CURRENT_HEAD="$(git -C "${ROOT_DIR}" rev-parse HEAD)"
fi

cat > "${STAMP_FILE}" <<EOF
GIT_HEAD=${CURRENT_HEAD}
TARGET_PLATFORM=${TARGET_PLATFORM}
BUILD_TYPE=${BUILD_TYPE}
EOF

echo "Built native launcher at ${BUILD_DIR}/${OUTPUT_NAME}"
