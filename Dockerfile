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

ARG AIRUNNER_INSTALL_PROFILES=core,llm-native,stt-native,art-python,tts-python,gui,development,computer-use

# Install system dependencies required by the selected runtime profiles.
RUN set -e; \
    profile_match() { \
        printf '%s' ",${AIRUNNER_INSTALL_PROFILES}," | \
            grep -Eq ",($1),"; \
    }; \
    packages="software-properties-common curl wget git build-essential"; \
    packages="$packages cmake pkg-config libprotobuf-dev"; \
    packages="$packages protobuf-compiler"; \
    if profile_match 'stt-native|tts-python|headless|desktop|all|all_dev|all_native|all_dev_native'; then \
        packages="$packages ffmpeg libsndfile1 portaudio19-dev"; \
        packages="$packages pulseaudio libasound2-dev"; \
    fi; \
    if profile_match 'gui|desktop|all|all_dev|all_native|all_dev_native|computer-use|computer_use'; then \
        packages="$packages libnss3 libxslt1.1 libxkbfile1"; \
        packages="$packages libx11-xcb1 libxcb-cursor0 libxcb-icccm4"; \
        packages="$packages libxcb-image0 libxcb-keysyms1"; \
        packages="$packages libxcb-randr0 libxcb-render-util0"; \
        packages="$packages libxcb-shape0 libxcb-xfixes0"; \
        packages="$packages libxcb-xinerama0 libxkbcommon-x11-0"; \
        packages="$packages libegl1 libgl1 libgles2"; \
        packages="$packages libfontconfig1 libdbus-1-3"; \
        packages="$packages libxcomposite1 libxdamage1 libxrandr2"; \
        packages="$packages libxtst6 libdrm2 libgbm1 libxss1"; \
        packages="$packages libcups2 libatk1.0-0"; \
        packages="$packages libatk-bridge2.0-0 xclip"; \
        packages="$packages scrot xdotool gnome-screenshot"; \
    fi; \
    if profile_match 'openvoice_jp|openvoice_kr|all_native|all_dev_native'; then \
        packages="$packages mecab libmecab-dev mecab-ipadic-utf8"; \
    fi; \
    apt-get update && apt-get install -y $packages && \
    rm -rf /var/lib/apt/lists/*

# Install Python 3.13 and tkinter when GUI automation is enabled.
RUN set -e; \
    add-apt-repository ppa:deadsnakes/ppa -y; \
    apt-get update; \
    packages="python3.13 python3.13-dev"; \
    if printf '%s' ",${AIRUNNER_INSTALL_PROFILES}," | \
        grep -Eq ',(gui|desktop|all|all_dev|all_native|all_dev_native|computer-use|computer_use),'; then \
        packages="$packages python3.13-tk"; \
    fi; \
    apt-get install -y $packages && rm -rf /var/lib/apt/lists/*

# Install pip for Python 3.13
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.13

# Upgrade pip tooling (install system-wide; no venv inside the container)
RUN python3.13 -m pip install --upgrade pip setuptools wheel

# Build llama-cpp-python from source when the llm-native profile is used.
# Default to CPU builds so local dev works without NVIDIA drivers.
# To enable CUDA builds, pass: --build-arg AIRUNNER_ENABLE_CUDA=1
ARG AIRUNNER_ENABLE_CUDA=0
ARG GGML_CUDA_ARCHITECTURES=
RUN set -e; \
    if printf '%s' ",${AIRUNNER_INSTALL_PROFILES}," | \
        grep -Eq ',(llm-native|headless|desktop|all|all_dev|all_native|all_dev_native),'; then \
        if [ "${AIRUNNER_ENABLE_CUDA}" = "1" ]; then \
            CUDA_STUB_DIR="/usr/local/cuda/targets/x86_64-linux/lib/stubs"; \
            if [ ! -f "${CUDA_STUB_DIR}/libcuda.so" ]; then \
                echo "CUDA stub libcuda.so not found at ${CUDA_STUB_DIR}/libcuda.so"; \
                exit 1; \
            fi; \
            ln -sf "${CUDA_STUB_DIR}/libcuda.so" \
                "${CUDA_STUB_DIR}/libcuda.so.1"; \
            export LD_LIBRARY_PATH="${CUDA_STUB_DIR}:${LD_LIBRARY_PATH:-}"; \
            export LIBRARY_PATH="${CUDA_STUB_DIR}:${LIBRARY_PATH:-}"; \
            export CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_EXE_LINKER_FLAGS=-Wl,-rpath-link,${CUDA_STUB_DIR}"; \
            if [ -n "${GGML_CUDA_ARCHITECTURES}" ]; then \
                export CMAKE_ARGS="${CMAKE_ARGS} -DGGML_CUDA_ARCHITECTURES=${GGML_CUDA_ARCHITECTURES} -DCMAKE_CUDA_ARCHITECTURES=${GGML_CUDA_ARCHITECTURES}"; \
            fi; \
        else \
            export CMAKE_ARGS="-DGGML_CUDA=off"; \
        fi; \
        export FORCE_CMAKE=1; \
        python3.13 -m pip install --no-cache-dir \
            --no-binary=llama-cpp-python \
            "llama-cpp-python==0.3.21"; \
    fi

# Set working directory
WORKDIR /app

# Copy project files
COPY setup.py pyproject.toml README.md ./
COPY src/ ./src/
COPY extensions/ ./extensions/

# Install airunner with the selected dependency profiles.
RUN python3.13 -m pip install -e ".[$AIRUNNER_INSTALL_PROFILES]"

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
