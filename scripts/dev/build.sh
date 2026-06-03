#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLEAN_BUILD=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --clean)
            CLEAN_BUILD=1
            shift
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Usage: $0 [--clean]" >&2
            exit 1
            ;;
    esac
done

echo "=== Building AI Runner native launcher ==="

BUILD_ARGS=()
if [[ "${CLEAN_BUILD}" == "1" ]]; then
    echo "Clean build requested..."
    BUILD_ARGS+=(--clean)
fi

"${ROOT_DIR}/scripts/build_airunner_launcher.sh" "${BUILD_ARGS[@]}"

echo ""
echo "Build complete."
echo "Run ./scripts/dev/run_services.sh to start the daemon, then"
echo "run 'cd airunner_web_client && npm run dev' for the web GUI."
