#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build/airunner-launcher"
BUILD_TYPE="${CMAKE_BUILD_TYPE:-RelWithDebInfo}"

cmake_args=(
  -S "${ROOT_DIR}/native/airunner_launcher"
  -B "${BUILD_DIR}"
  -DCMAKE_BUILD_TYPE="${BUILD_TYPE}"
)

if [[ -n "${CMAKE_GENERATOR:-}" ]]; then
  cmake_args+=( -G "${CMAKE_GENERATOR}" )
elif command -v ninja >/dev/null 2>&1; then
  cmake_args+=( -G Ninja )
fi

cmake "${cmake_args[@]}"
cmake --build "${BUILD_DIR}" --config "${BUILD_TYPE}"

echo "Built native launcher at ${BUILD_DIR}/airunner"