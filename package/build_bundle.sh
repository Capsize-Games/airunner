#!/usr/bin/env bash
#
# build_bundle.sh – Build the AI Runner end-user bundle for Linux.
#
# Prerequisites on the build host:
#   - CUDA toolkit 12.x (matching the version pinned in package/versions.txt)
#   - CMake >= 3.24
#   - curl, tar, gzip
#   - Node.js >= 20 (for Electron and React frontend build)
#
# This script mirrors the CI pipeline steps and is intended for local
# testing by developers who have the required toolchain installed.
#

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ELECTRON_DIR="${ROOT_DIR}/electron"
WEB_DIR="${ROOT_DIR}/client"
SERVICES_DIR="${ROOT_DIR}/server"
BUILD_DIR="${ROOT_DIR}/build/bundle"
RESOURCES_DIR="${ELECTRON_DIR}/resources"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

fail() { echo -e "${RED}ERROR:${NC} $*" >&2; exit 1; }
info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }

# ---------------------------------------------------------------------------
# Source the pinned versions from versions.txt
# ----------------------------------------------------------------------------
VERSIONS_FILE="${ROOT_DIR}/package/versions.txt"
declare -A VERSIONS

while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" == \#* ]] && continue
    VERSIONS["$key"]="$value"
done < "$VERSIONS_FILE"

PYTHON_VERSION="${VERSIONS[python]}"
PYTHON_BUILD_STANDALONE_VERSION="${VERSIONS[python-build-standalone]}"
LLAMA_CPP_TAG="${VERSIONS[llama.cpp]}"
WHISPER_CPP_TAG="${VERSIONS[whisper.cpp]}"
TORCH_INDEX="${VERSIONS[torch]}"

# ---------------------------------------------------------------------------
# Step 0 — Clean and prepare directories
# ---------------------------------------------------------------------------
rm -rf "$BUILD_DIR" "$RESOURCES_DIR"
mkdir -p "$BUILD_DIR" "$RESOURCES_DIR/python" "$RESOURCES_DIR/web"

# ---------------------------------------------------------------------------
# Step 1 — Download and extract python-build-standalone
#
# python-build-standalone is now hosted by astral-sh:
#   https://github.com/astral-sh/python-build-standalone
# Release tag is a date stamp (e.g. 20260602).
# Archive name format: cpython-{ver}+{tag}-{triple}-install_only.tar.gz
# ---------------------------------------------------------------------------
info "Downloading python-build-standalone ${PYTHON_BUILD_STANDALONE_VERSION}..."

PYTHON_ARCHIVE="cpython-${PYTHON_VERSION}+${PYTHON_BUILD_STANDALONE_VERSION}-x86_64-unknown-linux-gnu-install_only.tar.gz"
PYTHON_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PYTHON_BUILD_STANDALONE_VERSION}/${PYTHON_ARCHIVE}"

if [ ! -f "${BUILD_DIR}/${PYTHON_ARCHIVE}" ]; then
    info "Fetching ${PYTHON_URL}"
    curl -fsSL -o "${BUILD_DIR}/${PYTHON_ARCHIVE}" "$PYTHON_URL"
fi

info "Extracting python-build-standalone..."
tar -xzf "${BUILD_DIR}/${PYTHON_ARCHIVE}" -C "$BUILD_DIR"
EMBEDDED_PYTHON="${BUILD_DIR}/python"

# Verify the embedded Python works.
"${EMBEDDED_PYTHON}/bin/python3" --version

# ---------------------------------------------------------------------------
# Step 2 — Install Python dependencies into the embedded runtime
# ---------------------------------------------------------------------------
info "Installing Python dependencies..."

# pip install first
"${EMBEDDED_PYTHON}/bin/python3" -m pip install --upgrade pip setuptools wheel

# Install PyTorch with CUDA support first (large download).
info "Installing PyTorch with CUDA (${TORCH_INDEX})..."
"${EMBEDDED_PYTHON}/bin/python3" -m pip install \
    torch torchvision torchaudio \
    --index-url "https://download.pytorch.org/whl/${TORCH_INDEX}"

# Install the airunner services package with the bundle profile.
# The "headless" profile includes llm-native, stt-native, art-python, tts-python.
info "Installing airunner services [headless]..."
"${EMBEDDED_PYTHON}/bin/python3" -m pip install \
    -e "${SERVICES_DIR}[headless]"

# ---------------------------------------------------------------------------
# Step 3 — Build llama.cpp from source with CUDA
# ---------------------------------------------------------------------------
info "Building llama.cpp ${LLAMA_CPP_TAG} with CUDA..."

LLAMA_SRC="${BUILD_DIR}/llama.cpp"
if [ ! -d "$LLAMA_SRC" ]; then
    git clone --depth 1 --branch "${LLAMA_CPP_TAG}" \
        https://github.com/ggerganov/llama.cpp.git "$LLAMA_SRC"
fi

cmake -S "${LLAMA_SRC}" -B "${LLAMA_SRC}/build" \
    -DLLAMA_CUBLAS=on \
    -DCMAKE_CUDA_ARCHITECTURES=86 \
    -DBUILD_SHARED_LIBS=on \
    -DLLAMA_BUILD_TESTS=off \
    -DLLAMA_BUILD_EXAMPLES=off \
    -DCMAKE_BUILD_TYPE=Release

cmake --build "${LLAMA_SRC}/build" --config Release -j"$(nproc)"

# Find llama-cpp-python package directory inside the embedded Python.
LLAMA_CPP_LIBDIR=$(find "${EMBEDDED_PYTHON}" -path "*/site-packages/llama_cpp/lib" \
    -type d 2>/dev/null | head -1)

if [ -n "$LLAMA_CPP_LIBDIR" ]; then
    info "Placing libllama.so into ${LLAMA_CPP_LIBDIR}/"
    cp "${LLAMA_SRC}/build/libllama.so" "${LLAMA_CPP_LIBDIR}/"
else
    warn "Could not find llama_cpp/lib dir. Placing libllama.so in the Python lib directory as fallback."
    mkdir -p "${EMBEDDED_PYTHON}/lib"
    cp "${LLAMA_SRC}/build/libllama.so" "${EMBEDDED_PYTHON}/lib/"
fi

# ---------------------------------------------------------------------------
# Step 4 — Build whisper.cpp from source with CUDA
# ---------------------------------------------------------------------------
info "Building whisper.cpp ${WHISPER_CPP_TAG} with CUDA..."

WHISPER_SRC="${BUILD_DIR}/whisper.cpp"
if [ ! -d "$WHISPER_SRC" ]; then
    git clone --depth 1 --branch "${WHISPER_CPP_TAG}" \
        https://github.com/ggerganov/whisper.cpp.git "$WHISPER_SRC"
fi

cmake -S "${WHISPER_SRC}" -B "${WHISPER_SRC}/build" \
    -DGGML_CUDA=on \
    -DCMAKE_CUDA_ARCHITECTURES=86 \
    -DBUILD_SHARED_LIBS=on \
    -DWHISPER_BUILD_TESTS=off \
    -DWHISPER_BUILD_EXAMPLES=off \
    -DCMAKE_BUILD_TYPE=Release

cmake --build "${WHISPER_SRC}/build" --config Release -j"$(nproc)"

# Find whisper-cpp Python package directory.
WHISPER_CPP_LIBDIR=$(find "${EMBEDDED_PYTHON}" -path "*/site-packages/whisper_cpp/lib" \
    -type d 2>/dev/null | head -1)

if [ -n "$WHISPER_CPP_LIBDIR" ]; then
    info "Placing libwhisper.so into ${WHISPER_CPP_LIBDIR}/"
    cp "${WHISPER_SRC}/build/src/libwhisper.so" "${WHISPER_CPP_LIBDIR}/" 2>/dev/null || \
        cp "${WHISPER_SRC}/build/libwhisper.so" "${WHISPER_CPP_LIBDIR}/"
else
    warn "Could not find whisper_cpp/lib dir. Placing libwhisper.so in the Python lib directory as fallback."
    cp "${WHISPER_SRC}/build/src/libwhisper.so" "${EMBEDDED_PYTHON}/lib/" 2>/dev/null || \
        cp "${WHISPER_SRC}/build/libwhisper.so" "${EMBEDDED_PYTHON}/lib/"
fi

# ---------------------------------------------------------------------------
# Step 5 — Generate application icons
# ---------------------------------------------------------------------------
info "Generating application icons..."

"${EMBEDDED_PYTHON}/bin/python3" -c "
from PIL import Image, ImageDraw
import os
outdir = '${ROOT_DIR}/packaging/linux'
os.makedirs(outdir, exist_ok=True)
for size in [256, 128, 64, 48, 32, 24, 16]:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = max(2, size // 20)
    draw.rounded_rectangle(
        [margin, margin, size - margin - 1, size - margin - 1],
        radius=size // 5,
        fill=(88, 86, 214, 255),
    )
    img.save(os.path.join(outdir, f'{size}x{size}.png'))
img.save(os.path.join(outdir, 'icon.png'))
print('Icons generated')
"

# ---------------------------------------------------------------------------
# Step 6 — Build the React frontend
# ---------------------------------------------------------------------------
info "Building React frontend..."

if [ ! -d "${WEB_DIR}/node_modules" ]; then
    (cd "$WEB_DIR" && npm ci)
fi

(cd "$WEB_DIR" && VITE_API_BASE_URL="http://localhost:8080" npx vite build)

# ---------------------------------------------------------------------------
# Step 7 — Copy build artifacts into electron/resources/
# ---------------------------------------------------------------------------
info "Copying build artifacts into electron/resources/..."

# Copy the embedded Python runtime.
cp -a "${EMBEDDED_PYTHON}" "${RESOURCES_DIR}/python/"

# Copy the compiled React frontend.
cp -a "${WEB_DIR}/dist/"* "${RESOURCES_DIR}/web/"

# ---------------------------------------------------------------------------
# Step 8 — Build the Electron installer
# ---------------------------------------------------------------------------
info "Building Electron installer..."

if [ ! -d "${ELECTRON_DIR}/node_modules" ]; then
    (cd "$ELECTRON_DIR" && npm ci)
fi

(cd "$ELECTRON_DIR" && npm run build:linux)

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
info "Bundle build complete!"
info "Installer artifacts are in ${ELECTRON_DIR}/dist/"
ls -lh "${ELECTRON_DIR}/dist/"*.AppImage "${ELECTRON_DIR}/dist/"*.deb 2>/dev/null || \
    warn "No installer artifacts found. Check the electron-builder output above."
