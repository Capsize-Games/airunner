<#
.SYNOPSIS
    Build the AI Runner end-user bundle for Windows.

.DESCRIPTION
    This script mirrors the CI pipeline for Windows (NVIDIA CUDA) builds.
    Prerequisites on the build host:
      - CUDA toolkit 12.x (matching the version pinned in package/versions.txt)
      - CMake >= 3.24
      - Visual Studio 2022 with "Desktop development with C++" workload
      - Node.js >= 20
      - curl, tar
#>

$ErrorActionPreference = "Stop"
$ROOT_DIR = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ELECTRON_DIR = Join-Path $ROOT_DIR "electron"
$WEB_DIR = Join-Path $ROOT_DIR "client"
$SERVICES_DIR = Join-Path $ROOT_DIR "server"
$BUILD_DIR = Join-Path $ROOT_DIR "build\bundle"
$RESOURCES_DIR = Join-Path $ELECTRON_DIR "resources"

# ---------------------------------------------------------------------------
# Read pinned versions
# ---------------------------------------------------------------------------
$VERSIONS_FILE = Join-Path $ROOT_DIR "package\versions.txt"
$VERSIONS = @{}
Get-Content $VERSIONS_FILE | ForEach-Object {
    if ($_ -match "^([^#=]+)=(.+)$") {
        $VERSIONS[$matches[1]] = $matches[2]
    }
}

$PYTHON_BUILD_STANDALONE_VERSION = $VERSIONS["python-build-standalone"]
$LLAMA_CPP_TAG = $VERSIONS["llama.cpp"]
$WHISPER_CPP_TAG = $VERSIONS["whisper.cpp"]
$TORCH_INDEX = $VERSIONS["torch"]

Write-Host "=== AI Runner Bundle Build (Windows) ===" -ForegroundColor Green

# ---------------------------------------------------------------------------
# Step 0 – Clean and prepare directories
# ---------------------------------------------------------------------------
if (Test-Path $BUILD_DIR) { Remove-Item -Recurse -Force $BUILD_DIR }
if (Test-Path $RESOURCES_DIR) { Remove-Item -Recurse -Force $RESOURCES_DIR }
New-Item -ItemType Directory -Force -Path "$BUILD_DIR\python"
New-Item -ItemType Directory -Force -Path "$RESOURCES_DIR\python"
New-Item -ItemType Directory -Force -Path "$RESOURCES_DIR\web"

# ---------------------------------------------------------------------------
# Step 1 – Download and extract python-build-standalone
# ---------------------------------------------------------------------------
Write-Host "Downloading python-build-standalone ${PYTHON_BUILD_STANDALONE_VERSION}..." -ForegroundColor Green

$PYTHON_ARCHIVE = "cpython-3.13.${PYTHON_BUILD_STANDALONE_VERSION}-x86_64-pc-windows-msvc-install_only.tar.gz"
$PYTHON_URL = "https://github.com/indygreg/python-build-standalone/releases/download/${PYTHON_BUILD_STANDALONE_VERSION}/${PYTHON_ARCHIVE}"
$PYTHON_ARCHIVE_PATH = Join-Path $BUILD_DIR $PYTHON_ARCHIVE

if (-not (Test-Path $PYTHON_ARCHIVE_PATH)) {
    Invoke-WebRequest -Uri $PYTHON_URL -OutFile $PYTHON_ARCHIVE_PATH
}

Write-Host "Extracting python-build-standalone..." -ForegroundColor Green
tar -xzf $PYTHON_ARCHIVE_PATH -C $BUILD_DIR
$EMBEDDED_PYTHON = Join-Path $BUILD_DIR "python"

# Verify
& "$EMBEDDED_PYTHON\python.exe" --version

# ---------------------------------------------------------------------------
# Step 2 – Install Python dependencies into the embedded runtime
# ---------------------------------------------------------------------------
Write-Host "Installing Python dependencies..." -ForegroundColor Green

& "$EMBEDDED_PYTHON\python.exe" -m pip install --upgrade pip setuptools wheel

# Install PyTorch with CUDA support.
& "$EMBEDDED_PYTHON\python.exe" -m pip install `
    torch torchvision torchaudio `
    --index-url "https://download.pytorch.org/whl/${TORCH_INDEX}"

# Install the airunner services package with the headless profile.
& "$EMBEDDED_PYTHON\python.exe" -m pip install `
    -e "${SERVICES_DIR}[headless]"

# ---------------------------------------------------------------------------
# Step 3 – Build llama.cpp from source with CUDA
# ---------------------------------------------------------------------------
Write-Host "Building llama.cpp ${LLAMA_CPP_TAG} with CUDA..." -ForegroundColor Green

$LLAMA_SRC = Join-Path $BUILD_DIR "llama.cpp"
if (-not (Test-Path $LLAMA_SRC)) {
    git clone --depth 1 --branch $LLAMA_CPP_TAG `
        "https://github.com/ggerganov/llama.cpp.git" $LLAMA_SRC
}

cmake -S $LLAMA_SRC -B "$LLAMA_SRC/build" `
    -DGGML_CUDA=on `
    -DGGML_CUDA_ARCHITECTURES=86 `
    -DBUILD_SHARED_LIBS=on `
    -DLLAMA_BUILD_TESTS=off `
    -DLLAMA_BUILD_EXAMPLES=off `
    -DCMAKE_BUILD_TYPE=Release

cmake --build "$LLAMA_SRC/build" --config Release -j $env:NUMBER_OF_PROCESSORS

# Find llama-cpp-python package directory.
$LLAMA_CPP_DIR = Get-ChildItem -Path $EMBEDDED_PYTHON -Recurse -Directory `
    -Filter "llama_cpp" | Where-Object { $_.FullName -match "site-packages\\llama_cpp$" } |
    Select-Object -First 1

if ($LLAMA_CPP_DIR) {
    Write-Host "Placing llama.dll into $($LLAMA_CPP_DIR.FullName)\lib\" -ForegroundColor Green
    New-Item -ItemType Directory -Force -Path "$($LLAMA_CPP_DIR.FullName)\lib\"
    Copy-Item "$LLAMA_SRC\build\bin\Release\llama.dll" "$($LLAMA_CPP_DIR.FullName)\lib\"
} else {
    Write-Host "Warning: Could not find llama_cpp site-package dir." -ForegroundColor Yellow
    Copy-Item "$LLAMA_SRC\build\bin\Release\llama.dll" "$EMBEDDED_PYTHON\libs\"
}

# ---------------------------------------------------------------------------
# Step 4 – Build whisper.cpp from source with CUDA
# ---------------------------------------------------------------------------
Write-Host "Building whisper.cpp ${WHISPER_CPP_TAG} with CUDA..." -ForegroundColor Green

$WHISPER_SRC = Join-Path $BUILD_DIR "whisper.cpp"
if (-not (Test-Path $WHISPER_SRC)) {
    git clone --depth 1 --branch $WHISPER_CPP_TAG `
        "https://github.com/ggerganov/whisper.cpp.git" $WHISPER_SRC
}

cmake -S $WHISPER_SRC -B "$WHISPER_SRC/build" `
    -DGGML_CUDA=on `
    -DGGML_CUDA_ARCHITECTURES=86 `
    -DBUILD_SHARED_LIBS=on `
    -DWHISPER_BUILD_TESTS=off `
    -DWHISPER_BUILD_EXAMPLES=off `
    -DCMAKE_BUILD_TYPE=Release

cmake --build "$WHISPER_SRC/build" --config Release -j $env:NUMBER_OF_PROCESSORS

$WHISPER_CPP_DIR = Get-ChildItem -Path $EMBEDDED_PYTHON -Recurse -Directory `
    -Filter "whisper_cpp" | Where-Object { $_.FullName -match "site-packages\\whisper_cpp$" } |
    Select-Object -First 1

if ($WHISPER_CPP_DIR) {
    Write-Host "Placing whisper.dll into $($WHISPER_CPP_DIR.FullName)\lib\" -ForegroundColor Green
    New-Item -ItemType Directory -Force -Path "$($WHISPER_CPP_DIR.FullName)\lib\"
    Copy-Item "$WHISPER_SRC\build\bin\Release\whisper.dll" "$($WHISPER_CPP_DIR.FullName)\lib\"
} else {
    Write-Host "Warning: Could not find whisper_cpp site-package dir." -ForegroundColor Yellow
    Copy-Item "$WHISPER_SRC\build\bin\Release\whisper.dll" "$EMBEDDED_PYTHON\libs\"
}

# ---------------------------------------------------------------------------
# Step 5 – Build the React frontend
# ---------------------------------------------------------------------------
Write-Host "Building React frontend..." -ForegroundColor Green

if (-not (Test-Path "$WEB_DIR\node_modules")) {
    Push-Location $WEB_DIR
    npm ci
    Pop-Location
}

$env:VITE_API_BASE_URL = "http://localhost:8080"
Push-Location $WEB_DIR
npm run build
Pop-Location

# ---------------------------------------------------------------------------
# Step 6 – Copy build artifacts into electron/resources/
# ---------------------------------------------------------------------------
Write-Host "Copying build artifacts into electron/resources/..." -ForegroundColor Green

Copy-Item -Recurse "$EMBEDDED_PYTHON\*" "$RESOURCES_DIR\python\"
Copy-Item -Recurse "$WEB_DIR\dist\*" "$RESOURCES_DIR\web\"

# ---------------------------------------------------------------------------
# Step 7 – Build the Electron installer
# ---------------------------------------------------------------------------
Write-Host "Building Electron installer..." -ForegroundColor Green

if (-not (Test-Path "$ELECTRON_DIR\node_modules")) {
    Push-Location $ELECTRON_DIR
    npm ci
    Pop-Location
}

Push-Location $ELECTRON_DIR
npm run build:windows
Pop-Location

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
Write-Host "Bundle build complete!" -ForegroundColor Green
Write-Host "Installer artifacts are in $ELECTRON_DIR\dist\" -ForegroundColor Green
Get-ChildItem "$ELECTRON_DIR\dist\*.exe"
