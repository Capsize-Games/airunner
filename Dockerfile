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
    python3.13-venv \
    python3.13-dev \
    python3.13-tk \
    && rm -rf /var/lib/apt/lists/*

# Install pip for Python 3.13
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.13

# Create virtual environment
RUN python3.13 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel

# Set working directory
WORKDIR /app

# Copy project files
COPY setup.py pyproject.toml README.md ./
COPY src/ ./src/

# Install airunner with all dependencies including computer_use
RUN pip install -e ".[all_dev,computer_use]"

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV AIRUNNER_ENVIRONMENT=production
ENV HF_HOME=/data/huggingface
ENV AIRUNNER_DATA_DIR=/data/airunner

# Expose the API port (used in headless mode)
EXPOSE 8080

# Health check for headless mode (will fail gracefully in GUI mode)
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 0

# Use entrypoint script to handle GUI vs headless
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Default to GUI mode (no arguments = GUI)
CMD []
