#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build/airunner-launcher"
LAUNCHER_BIN="${BUILD_DIR}/airunner"

if [[ ! -x "${LAUNCHER_BIN}" ]]; then
  "${ROOT_DIR}/scripts/build_airunner_launcher.sh"
fi

exec "${LAUNCHER_BIN}" --mode dev --repo-root "${ROOT_DIR}" "$@"