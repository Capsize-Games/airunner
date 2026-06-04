#!/usr/bin/env bash
#
# build_bundle.sh – Build the AI Runner end-user bundle for Linux.
#
# Prerequisites on the build host:
#   - CUDA toolkit 12.x (matching the version pinned in package/versions.txt)
#   - CMake >= 3.24
#   - curl, tar, gzip
#   - Node.js >= 20 (for Electron and React frontend build)
#   - Docker (optional, for building Python dependencies in a clean environment)
#
# This script mirrors the CI pipeline steps and is intended for local
# testing by developers who have the required toolchain installed.
#

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ELECTRON_DIR="${ROOT_DIR}/electron"
WEB_DIR="${ROOT_DIR}/airunner_web_client"
SERVICES_DIR="${ROOT_DIR}/services"
BUILD_DIR="${ROOT_DIR}/build/bundle"
RESOURCES_DIR="${ELECTRON_DIR}/resources"
VENV_DIR="${BUILD_DIR}/venv"

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

PYTHON_BUILD_STANDALONE_VERSION="${VERSIONS[python-build-standalone]}"
LLAMA_CPP_TAG="${VERSIONS[llama.cpp]}"
WHISPER_CPP_TAG="${VERSIONS[whisper.cpp]}"
CUDA_VERSION="${VERSIONS[cuda]}"
TORCH_INDEX="${VERSIONS[torch]}"

# ---------------------------------------------------------------------------
# Step 0 – Clean and prepare directories
# ---------------------------------------------------------------------------
rm -rf "$BUILD_DIR" "$RESOURCES_DIR"
mkdir -p "$BUILD_DIR" "$RESOURCES_DIR/python" "$RESOURCES_DIR/web"

# ---------------------------------------------------------------------------
# Step 1 – Download and extract python-build-standalone
# ---------------------------------------------------------------------------
info "Downloading python-build-standalone ${PYTHON_BUILD_STANDALONE_VERSION}..."

PYTHON_ARCHIVE="cpython-3.13.${PYTHON_BUILD_STANDALONE_VERSION}-x86_64-unknown-linux-gnu-install_only.tar.gz"
PYTHON_URL="https://github.com/indygreg/python-build-standalone/releases/download/${PYTHON_BUILD_STANDALONE_VERSION}/${PYTHON_ARCHIVE}"

if [ ! -f "${BUILD_DIR}/${PYTHON_ARCHIVE}" ]; then
    curl -fsSL -o "${BUILD_DIR}/${PYTHON_ARCHIVE}" "$PYTHON_URL"
fi

info "Extracting python-build-standalone..."
tar -xzf "${BUILD_DIR}/${PYTHON_ARCHIVE}" -C "$BUILD_DIR"
EMBEDDED_PYTHON="${BUILD_DIR}/python"

# Verify the embedded Python works.
"${EMBEDDED_PYTHON}/bin/python3" --version

# ---------------------------------------------------------------------------
# Step 2 – Install Python dependencies into the embedded runtime
# ---------------------------------------------------------------------------
info "Installing Python dependencies..."

# pip install first
"${EMBEDDED_PYTHON}/bin/python3" -m pip install --upgrade pip setuptools wheel

# Install PyTorch with CUDA support first (large download).
"${EMBEDDED_PYTHON}/bin/python3" -m pip install \
    torch torchvision torchaudio \
    --index-url "https://download.pytorch.org/whl/${TORCH_INDEX}"

# Install the airunner services package with the bundle profile.
# The "headless" profile includes llm-native, stt-native, art-python, tts-python.
"${EMBEDDED_PYTHON}/bin/python3" -m pip install \
    -e "${SERVICES_DIR}[headless]"

# ---------------------------------------------------------------------------
# Step 3 – Build llama.cpp from source with CUDA
# ---------------------------------------------------------------------------
info "Building llama.cpp ${LLAMA_CPP_TAG} with CUDA..."

LLAMA_SRC="${BUILD_DIR}/llama.cpp"
if [ ! -d "$LLAMA_SRC" ]; then
    git clone --depth 1 --branch "${LLAMA_CPP_TAG}" \
        https://github.com/ggerganov/llama.cpp.git "$LLAMA_SRC"
fi

cmake -B "${LLAMA_SRC}/build" \
    -DGGML_CUDA=on \
    -DGGML_CUDA_ARCHITECTURES=86 \
    -DBUILD_SHARED_LIBS=on \
    -DLLAMA_BUILD_TESTS=off \
    -DLLAMA_BUILD_EXAMPLES=off \
    -DCMAKE_BUILD_TYPE=Release

cmake --build "${LLAMA_SRC}/build" --config Release -j"$(nproc)"

# Find llama-cpp-python package directory inside the embedded Python.
LLAMA_CPP_PYTHON_DIR=$(find "${EMBEDDED_PYTHON}" -type d -name "llama_cpp" \
    -path "*/site-packages/llama_cpp" 2>/dev/null | head -1)

if [ -z "$LLAMA_CPP_PYTHON_DIR" ]; then
    # Try alternative discovery: find the llama_cpp package in site-packages.
    LLAMA_CPP_PYTHON_DIR=$(find "${EMBEDDED_PYTHON}" -path "*/site-packages/llama_cpp" \
        -type d 2>/dev/null | head -1)
fi

if [ -n "$LLAMA_CPP_PYTHON_DIR" ]; then
    info "Placing libllama.so into ${LLAMA_CPP_PYTHON_DIR}/lib/"
    mkdir -p "${LLAMA_CPP_PYTHON_DIR}/lib"
    cp "${LLAMA_SRC}/build/src/libllama.so" "${LLAMA_CPP_PYTHON_DIR}/lib/"
else
    warn "Could not find llama_cpp site-package dir. Placing libllama.so in the Python lib directory as fallback."
    mkdir -p "${EMBEDDED_PYTHON}/lib"
    cp "${LLAMA_SRC}/build/src/libllama.so" "${EMBEDDED_PYTHON}/lib/"
fi

# ---------------------------------------------------------------------------
# Step 4 – Build whisper.cpp from source with CUDA
# ---------------------------------------------------------------------------
info "Building whisper.cpp ${WHISPER_CPP_TAG} with CUDA..."

WHISPER_SRC="${BUILD_DIR}/whisper.cpp"
if [ ! -d "$WHISPER_SRC" ]; then
    git clone --depth 1 --branch "${WHISPER_CPP_TAG}" \
        https://github.com/ggerganov/whisper.cpp.git "$WHISPER_SRC"
fi

cmake -B "${WHISPER_SRC}/build" \
    -DGGML_CUDA=on \
    -DGGML_CUDA_ARCHITECTURES=86 \
    -DBUILD_SHARED_LIBS=on \
    -DWHISPER_BUILD_TESTS=off \
    -DWHISPER_BUILD_EXAMPLES=off \
    -DCMAKE_BUILD_TYPE=Release

cmake --build "${WHISPER_SRC}/build" --config Release -j"$(nproc)"

# Find whisper-cpp Python package directory.
WHISPER_CPP_PYTHON_DIR=$(find "${EMBEDDED_PYTHON}" -type d -name "whisper_cpp" \
    -path "*/site-packages/whisper_cpp" 2>/dev/null | head -1)

if [ -z "$WHISPER_CPP_PYTHON_DIR" ]; then
    WHISPER_CPP_PYTHON_DIR=$(find "${EMBEDDED_PYTHON}" -path "*/site-packages/whisper_cpp" \
        -type d 2>/dev/null | head -1)
fi

if [ -n "$WHISPER_CPP_PYTHON_DIR" ]; then
    info "Placing libwhisper.so into ${WHISPER_CPP_PYTHON_DIR}/lib/"
    mkdir -p "${WHISPER_CPP_PYTHON_DIR}/lib"
    cp "${WHISPER_SRC}/build/src/libwhisper.so" "${WHISPER_CPP_PYTHON_DIR}/lib/"
else
    warn "Could not find whisper_cpp site-package dir. Placing libwhisper.so in the Python lib directory as fallback."
    cp "${WHISPER_SRC}/build/src/libwhisper.so" "${EMBEDDED_PYTHON}/lib/"
fi

# ---------------------------------------------------------------------------
# Step 5 – Build the React frontend
# ---------------------------------------------------------------------------
info "Building React frontend..."

if [ ! -d "${WEB_DIR}/node_modules" ]; then
    (cd "$WEB_DIR" && npm ci)
fi

VITE_API_BASE_URL="http://localhost:8080" \
    (cd "$WEB_DIR" && npm run build)

# ---------------------------------------------------------------------------
# Step 6 – Copy build artifacts into electron/resources/
# ---------------------------------------------------------------------------
info "Copying build artifacts into electron/resources/..."

# Copy the embedded Python runtime (stripping unnecessary files).
cp -a "${EMBEDDED_PYTHON}" "${RESOURCES_DIR}/python/"

# Copy the compiled React frontend.
cp -a "${WEB_DIR}/dist/"* "${RESOURCES_DIR}/web/"

# ---------------------------------------------------------------------------
# Step 7 – Build the Electron installer
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
