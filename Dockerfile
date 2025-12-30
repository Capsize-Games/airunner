# Dockerfile for AI Runner - supports both headless server and GUI modes
# Provides HTTP API for LLM, Art generation, TTS, STT, and Vision
# Can also run full PySide6 GUI with X11 forwarding
#
# Usage:
#   GUI mode:      docker compose run --rm airunner
#   Headless mode: docker compose run --rm airunner --headless

FROM nvidia/cuda:12.9.1-devel-ubuntu24.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies including X11/Qt requirements for GUI
RUN apt-get update && apt-get install -y \
    software-properties-common \
    curl \
    wget \
    git \
    build-essential \
    cmake \
    pkg-config \
    libprotobuf-dev \
    protobuf-compiler \
    mecab \
    libmecab-dev \
    mecab-ipadic-utf8 \
    ffmpeg \
    libsndfile1 \
    portaudio19-dev \
    # PulseAudio for audio
    pulseaudio \
    libasound2-dev \
    # Install ALL Qt6 WebEngine dependencies via the package manager
    # This pulls in all required libraries for QtWebEngine
    libnss3 \
    libxslt1.1 \
    libxkbfile1 \
    # X11 and XCB libraries
    libx11-xcb1 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxkbcommon-x11-0 \
    # OpenGL
    libegl1 \
    libgl1 \
    libgles2 \
    # Additional GUI deps
    libfontconfig1 \
    libdbus-1-3 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxtst6 \
    libdrm2 \
    libgbm1 \
    libxss1 \
    libcups2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    # Clipboard support
    xclip \
    # pyautogui dependencies for computer use / desktop automation
    python3-tk \
    python3-dev \
    scrot \
    xdotool \
    gnome-screenshot \
    && rm -rf /var/lib/apt/lists/*

# Install Python 3.13 from deadsnakes PPA (including tkinter for pyautogui)
RUN add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && \
    apt-get install -y \
    python3.13 \
    python3.13-dev \
    python3.13-tk \
    && rm -rf /var/lib/apt/lists/*

# Install pip for Python 3.13
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.13

# Upgrade pip tooling (install system-wide; no venv inside the container)
RUN python3.13 -m pip install --upgrade pip setuptools wheel

# Build llama-cpp-python from source.
# Default to CPU builds so local dev works without NVIDIA drivers.
# To enable CUDA builds, pass: --build-arg AIRUNNER_ENABLE_CUDA=1
ARG AIRUNNER_ENABLE_CUDA=0
ARG GGML_CUDA_ARCHITECTURES=90
RUN set -e; \
    if [ "${AIRUNNER_ENABLE_CUDA}" = "1" ]; then \
    CUDA_STUB_DIR="/usr/local/cuda/targets/x86_64-linux/lib/stubs"; \
    if [ ! -f "${CUDA_STUB_DIR}/libcuda.so" ]; then \
    echo "CUDA stub libcuda.so not found at ${CUDA_STUB_DIR}/libcuda.so"; \
    exit 1; \
    fi; \
    ln -sf "${CUDA_STUB_DIR}/libcuda.so" "${CUDA_STUB_DIR}/libcuda.so.1"; \
    export LD_LIBRARY_PATH="${CUDA_STUB_DIR}:${LD_LIBRARY_PATH:-}"; \
    export LIBRARY_PATH="${CUDA_STUB_DIR}:${LIBRARY_PATH:-}"; \
    export CMAKE_ARGS="-DGGML_CUDA=on -DGGML_CUDA_ARCHITECTURES=${GGML_CUDA_ARCHITECTURES} -DCMAKE_CUDA_ARCHITECTURES=${GGML_CUDA_ARCHITECTURES} -DCMAKE_EXE_LINKER_FLAGS=-Wl,-rpath-link,${CUDA_STUB_DIR}"; \
    else \
    export CMAKE_ARGS="-DGGML_CUDA=off"; \
    fi; \
    export FORCE_CMAKE=1; \
    python3.13 -m pip install --no-cache-dir --no-binary=llama-cpp-python "llama-cpp-python==0.3.16"

# Set working directory
WORKDIR /app

# Copy project files
COPY setup.py pyproject.toml README.md ./
COPY src/ ./src/
COPY extensions/ ./extensions/

# Install airunner with all dependencies including computer_use
RUN python3.13 -m pip install -e ".[all_dev,computer_use]"

# Create non-root user for running the container
# docker-compose may override the runtime UID/GID; avoid hard-coding 1000 here
RUN set -eux; \
    if ! getent group airunner >/dev/null; then groupadd -r airunner; fi; \
    if ! id -u airunner >/dev/null 2>&1; then useradd -r -g airunner -m -s /bin/bash airunner; fi; \
    mkdir -p /home/airunner/.local/share/airunner; \
    mkdir -p /home/airunner/.cache/huggingface; \
    chown -R airunner:airunner /home/airunner; \
    chown -R airunner:airunner /app; \
    true

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV AIRUNNER_ENVIRONMENT=production
ENV HOME=/home/airunner
ENV HF_HOME=/home/airunner/.cache/huggingface
ENV AIRUNNER_DATA_DIR=/home/airunner/.local/share/airunner

# Expose the API port (used in headless mode)
EXPOSE 8080

# Health check for headless mode (will fail gracefully in GUI mode)
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 0

# Use entrypoint script to handle GUI vs headless
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Default to GUI mode (no arguments = GUI)
CMD []
