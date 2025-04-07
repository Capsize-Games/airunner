# Base image with CUDA and cuDNN already installed
FROM nvidia/cuda:12.2.2-cudnn9-runtime-ubuntu22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV DEBCONF_NOWARNINGS=yes
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3.10-venv python3-pip python3.10-distutils \
    build-essential git wget vim tmux \
    libffi-dev libssl-dev libgl1-mesa-dev libjpeg-dev zlib1g-dev libpng-dev \
    cmake ninja-build xclip xserver-xorg xvfb ffmpeg \
    portaudio19-dev alsa-utils libasound2-plugins espeak \
    dbus-x11 x11-xserver-utils x11-utils xauth \
    fontconfig fonts-liberation \
    libxcb-cursor0 libxcb-xinput0 libxcb-xfixes0 libxcomposite1 \
    libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 \
    libxcb-render-util0 libxcb-xinerama0 libxcb-xkb1 libxcb-glx0 \
    libxcb-shape0 libxcb-shm0 libxcb-sync1 libxcb-dri2-0 libxcb-dri3-0 \
    libxcb-present0 libxkbcommon-x11-0 libx11-xcb1 libxcb1 \
    gstreamer1.0-gl libglvnd0 libgl1 libglx0 libegl1 libxext6 libx11-6 \
 && rm -rf /var/lib/apt/lists/*

# Set environment for CUDA
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=$CUDA_HOME/bin:$PATH
ENV LD_LIBRARY_PATH=$CUDA_HOME/lib64:/usr/local/cuda/extras/CUPTI/lib64:$LD_LIBRARY_PATH

# Create user
ARG HOST_UID=1000
ARG HOST_GID=1000
RUN groupadd -g ${HOST_GID} appuser && \
    useradd -m -u ${HOST_UID} -g ${HOST_GID} appuser && \
    groupadd -g 1001 airunner_group && \
    usermod -aG airunner_group appuser && \
    mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix && \
    chown -R appuser:appuser /app

USER appuser
WORKDIR /app

# Upgrade pip and install Python dependencies (minimal here)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
 && pip install --no-cache-dir nvidia-pyindex \
 && pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Clone and install OpenVoice + MeloTTS
RUN git clone https://github.com/myshell-ai/OpenVoice.git && \
    pip install -e OpenVoice && \
    git clone https://github.com/myshell-ai/MeloTTS.git && \
    cd MeloTTS && git checkout -b v0.1.2 && pip install -e . && cd ..

# Download unidic
RUN python3 -m unidic download

# Final install of app requirements
COPY --chown=appuser:appuser . /app/
RUN pip install --no-cache-dir -e .[gui,linux,dev,art,llm,llm_weather,tts] && \
    pip install -U langchain-community mediapipe timm && \
    python3 -c "from accelerate.utils import write_basic_config; write_basic_config(mixed_precision='fp16')" && \
    python3 -c "import nltk; nltk.download('punkt')"

CMD ["/bin/bash"]
