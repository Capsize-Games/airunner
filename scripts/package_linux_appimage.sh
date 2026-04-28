#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUNDLE_DIR="$ROOT_DIR/build/end-user-bundles/linux/desktop"
OUTPUT_DIR="$ROOT_DIR/dist"
WORK_DIR="$ROOT_DIR/build/appimage"
VERSION=""

usage() {
    cat <<'EOF'
Usage: ./scripts/package_linux_appimage.sh [options]

Options:
  --bundle-dir PATH   Built Linux bundle directory
  --output-dir PATH   AppImage output directory
  --work-dir PATH     Temporary AppDir work directory
  --version VERSION   Override AIRunner version
  -h, --help          Show this help text
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --bundle-dir)
                BUNDLE_DIR="$2"
                shift 2
                ;;
            --output-dir)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --work-dir)
                WORK_DIR="$2"
                shift 2
                ;;
            --version)
                VERSION="$2"
                shift 2
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

detect_version() {
    if [[ -n "$VERSION" ]]; then
        echo "$VERSION"
        return
    fi
    sed -n 's/^[[:space:]]*version="\([0-9.]*\)",$/\1/p' "$ROOT_DIR/setup.py" | head -n 1
}

download_appimagetool() {
    local tool_dir="$WORK_DIR/tools"
    local tool_path="$tool_dir/appimagetool.AppImage"

    mkdir -p "$tool_dir"
    if [[ -f "$tool_path" ]]; then
        echo "$tool_path"
        return
    fi

    curl -fL \
        -o "$tool_path" \
        https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x "$tool_path"
    echo "$tool_path"
}

main() {
    parse_args "$@"

    local version
    local appdir
    local appimage_name
    local tool_path

    version="$(detect_version)"
    appdir="$WORK_DIR/AIRunner.AppDir"
    appimage_name="airunner-${version}-linux-x86_64.AppImage"

    rm -rf "$appdir"
    mkdir -p "$appdir/usr/lib/airunner"
    mkdir -p "$OUTPUT_DIR"

    cp -a "$BUNDLE_DIR"/. "$appdir/usr/lib/airunner/"
    cp "$BUNDLE_DIR/share/applications/airunner.desktop" "$appdir/airunner.desktop"
    cp "$BUNDLE_DIR/share/icons/hicolor/64x64/apps/airunner.png" "$appdir/airunner.png"

    cat > "$appdir/AppRun" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AIRUNNER_BUNDLE_ROOT="$HERE/usr/lib/airunner"
export LD_LIBRARY_PATH="$HERE/usr/lib/airunner/app/site-packages/PySide6/Qt/lib:${LD_LIBRARY_PATH:-}"
export QT_PLUGIN_PATH="$HERE/usr/lib/airunner/app/site-packages/PySide6/Qt/plugins"
exec "$HERE/usr/lib/airunner/bin/airunner" "$@"
EOF
    chmod +x "$appdir/AppRun"

    tool_path="$(download_appimagetool)"
    APPIMAGE_EXTRACT_AND_RUN=1 \
        "$tool_path" \
        "$appdir" \
        "$OUTPUT_DIR/$appimage_name"

    echo "$OUTPUT_DIR/$appimage_name"
}

main "$@"