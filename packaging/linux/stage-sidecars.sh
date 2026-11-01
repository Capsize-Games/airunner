#!/usr/bin/env bash
# Stage named regular-file sidecars and extend the candidate manifest.
# Archive paths are validated but never extracted to the filesystem.
# shellcheck shell=bash
set -euo pipefail

HERE=$(cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$HERE/../../scripts/stage_native_sidecars.py" "$@"
