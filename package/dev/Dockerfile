FROM ubuntu:22.04 AS base_image
ENV DEBIAN_FRONTEND=noninteractive
ENV DEBCONF_NOWARNINGS="yes"
WORKDIR /app

ARG INSTALL_XCB_CURSOR=0
ARG HOST_UID=$HOST_UID
ARG HOST_GID=$HOST_GID

RUN set -eux; \
    echo "Creating group ${HOST_GID} and user ${HOST_UID}"; \
    if ! getent group ${HOST_GID} > /dev/null 2>&1; then \
        groupadd -g ${HOST_GID} appgroup; \
        echo "Group appgroup (${HOST_GID}) created."; \
    else \
        # If group exists, capture its name for potential use in useradd/usermod
        EXISTING_GROUP_NAME=$(getent group ${HOST_GID} | cut -d: -f1); \
        echo "Group with GID ${HOST_GID} (name: ${EXISTING_GROUP_NAME}) already exists."; \
    fi; \
    # Ensure the target group name exists for useradd
    TARGET_GROUP_NAME=$(getent group ${HOST_GID} | cut -d: -f1); \
    if ! id -u ${HOST_UID} > /dev/null 2>&1; then \
        useradd --system --create-home --no-log-init -u ${HOST_UID} -g ${TARGET_GROUP_NAME} -s /bin/bash appuser; \
        echo "User appuser (${HOST_UID}) created with primary group ${TARGET_GROUP_NAME} (${HOST_GID})."; \
    else \
        # If user exists, ensure their primary group is correct
        usermod -g ${HOST_GID} $(getent passwd ${HOST_UID} | cut -d: -f1); \
        echo "User with UID ${HOST_UID} already exists. Ensured primary group GID is ${HOST_GID}."; \
    fi

# Install system dependencies
RUN apt-get update && apt-get install -y software-properties-common && \
 add-apt-repository ppa:ubuntu-toolchain-r/test && \
 apt-get update && apt-get install -y \
 build-essential \
 libssl-dev \
 zlib1g-dev \
 libbz2-dev \
 libreadline-dev \
 libsqlite3-dev \
 wget \
 curl \
 llvm \
 libncurses5-dev \
 libncursesw5-dev \
 xz-utils \
 tk-dev \
 libffi-dev \
 liblzma-dev \
 git \
 libgl1-mesa-dev \
 libjpeg-dev \
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
 libnss3 \
 libatk1.0-0 \
 libxkbcommon-x11-0 \
 libgtk-3-0 \
 libpq5 \
 libodbc2 \
 libmysqlclient21 \
 libpcsclite1 \
 libpcsclite-dev \
 libcups2 \
 libcups2-dev \
 libspeechd2 \
 libspeechd-dev \
 libsox3 \
 libsox-dev \
 libtbb12 \
 libtbb-dev \
 libtbb2 \
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
 libportaudio2 \
 gnupg && \
 rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install Python 3.13.3 from source
RUN cd /tmp && \
    wget https://www.python.org/ftp/python/3.13.3/Python-3.13.3.tgz && \
    tar -xf Python-3.13.3.tgz && \
    cd Python-3.13.3 && \
    ./configure --enable-optimizations && \
    make -j$(nproc) && \
    make altinstall && \
    cd .. && \
    rm -rf Python-3.13.3 Python-3.13.3.tgz

# Make Python 3.13.3 the default
RUN ln -sf /usr/local/bin/python3.13 /usr/local/bin/python && \
    ln -sf /usr/local/bin/python3.13 /usr/local/bin/python3 && \
    ln -sf /usr/local/bin/pip3.13 /usr/local/bin/pip && \
    ln -sf /usr/local/bin/pip3.13 /usr/local/bin/pip3

# Update PATH to include Python 3.13.3
ENV PATH="/usr/local/bin:${PATH}"

# Set environment variables for CUDA and cuDNN, nvidia runtime and path
ENV PATH=/usr/local/cuda/bin:$PATH
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=$CUDA_HOME/bin:$PATH
ENV LD_LIBRARY_PATH=$VIRTUAL_ENV/lib/python3.13/site-packages/PySide6/Qt/lib:/ususe_grr/lib/x86_64-linux-gnu:$CUDA_HOME/lib64:$CUDA_HOME/extras/CUPTI/lib64
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Copy the application files first
COPY --chown=${HOST_UID}:${HOST_GID} . /app/

# Install Python packages at build time instead of runtime
USER root
RUN pip3.13 install --no-cache-dir pip setuptools wheel --upgrade && \
    pip3.13 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128 && \
    cd /app && pip3.13 install --no-cache-dir -e .[all_dev] -U langchain-community && \
    pip3.13 install -U timm && \
    python3.13 -c "import nltk; nltk.download('punkt')" && \
    rm -rf /tmp/* /var/tmp/* /root/.cache/pip

USER ${HOST_UID}:${HOST_GID}
WORKDIR /app

CMD ["/bin/bash"]
