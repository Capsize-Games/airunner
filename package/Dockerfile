FROM ubuntu:22.04 AS base_image
ENV DEBIAN_FRONTEND=noninteractive
ENV DEBCONF_NOWARNINGS="yes"
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y software-properties-common && \
 add-apt-repository ppa:ubuntu-toolchain-r/test && \
 apt-get update && apt-get install -y \
 python3.10 \
 python3.10-venv \
 python3-pip \
 python3.10-distutils \
 build-essential \
 git \
 wget \
 libffi-dev \
 libssl-dev \
 libgl1-mesa-dev \
 libjpeg-dev \
 zlib1g-dev \
 libpng-dev \
 cmake \
 ninja-build \
 xclip \
 xserver-xorg \
 xvfb \
 ffmpeg \
 # Qt6 dependencies for XCB
 libxcb-cursor0 \
 libxcb-xinput0 \
 libxcb-xfixes0 \
 libxcomposite1 \
 libxcb-icccm4 \
 libxcb-image0 \
 libxcb-keysyms1 \
 libxcb-randr0 \
 libxcb-render-util0 \
 libxcb-xinerama0 \
 libxcb-xkb1 \
 libxcb-glx0 \
 libxcb-shape0 \
 libxcb-shm0 \
 libxcb-sync1 \
 libxcb-dri2-0 \
 libxcb-dri3-0 \
 libxcb-present0 \
 libxkbcommon-x11-0 \
 libx11-xcb1 \
 libxcb1 \
 gstreamer1.0-gl \
 x11-utils \
 patchelf \
 mesa-utils \
 xauth \
 # Fontconfig and fonts
 fontconfig \
 fonts-liberation \
 mesa-utils \
 libglvnd0 \
 libgl1 \
 libglx0 \
 libegl1 \
 libxext6 \
 libx11-6 \
 x11-apps \
 # Add these new X11-related packages
 dbus-x11 \
 x11-xserver-utils \
 portaudio19-dev \
 alsa-utils \
 libasound2-plugins \
 espeak \
 vim \
 tmux \
 libstdc++6 \
 wget \
 gnupg && \
 rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set environment variables for CUDA and cuDNN, nvidia runtime and path
ENV PATH=/usr/local/cuda/bin:$PATH
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=$CUDA_HOME/bin:$PATH
ENV LD_LIBRARY_PATH=$VIRTUAL_ENV/lib/python3.10/site-packages/PySide6/Qt/lib:/ususe_grr/lib/x86_64-linux-gnu:$CUDA_HOME/lib64:$CUDA_HOME/extras/CUPTI/lib64
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Dynamically set the UID and GID for appuser
ARG INSTALL_XCB_CURSOR=0
ARG HOST_UID=1000
ARG HOST_GID=1000
RUN if [ "$INSTALL_XCB_CURSOR" = "1" ]; then \
        apt-get update && apt-get install -y libxcb-cursor0; \
    fi && \
 groupadd -g 1000 appuser && useradd -m -u 1000 -g 1000 appuser && \
 groupmod -g ${HOST_GID} appuser && usermod -u ${HOST_UID} -g ${HOST_GID} appuser && \
 chown -R appuser:appuser /app && \
 groupadd -g 1001 airunner_group && usermod -aG airunner_group appuser && \
 apt-get update && apt-get install -y x11-xserver-utils && \
 mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix
COPY --chown=appuser:appuser . /app/
COPY ./package/entrypoint.sh /app/package/entrypoint.sh
RUN chmod +x /app/package/entrypoint.sh

# Download butler
WORKDIR /home/appuser/
RUN mkdir -p /home/appuser/butler && \
    cd /home/appuser/butler && \
    wget https://dl.itch.ovh/butler/linux-amd64/head/butler && chmod +x butler && \
    cd /home/appuser

CMD ["/bin/bash"]