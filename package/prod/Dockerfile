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
RUN apt-get update && \
 apt-get install -y \software-properties-common && \
 add-apt-repository ppa:ubuntu-toolchain-r/test && \
 apt-get update && \
 apt-get install -y \
 make \
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
 nvidia-cuda-toolkit \
 pipewire \
 libportaudio2 \
 libxcb-cursor0 \
 gnupg \
 gpg-agent \
 pinentry-curses \
 espeak \
 xclip \
 cmake \
 qt6-qpa-plugins \
 qt6-wayland \
 qt6-gtk-platformtheme \
 libgl1-mesa-dev \
 libjpeg-dev \
 libpng-dev \
 ninja-build \
 ffmpeg \
 # Qt6 dependencies for XCB
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
 vim \
 tmux \
 libstdc++6 \
 gnupg \
 # NSS libraries for WebEngine
 libnss3 \
 libnss3-dev \
 libnspr4 \
 libnspr4-dev \
 # GTK libraries
 libgtk-3-0 \
 libgtk-3-dev \
 libgdk-pixbuf2.0-dev \
 libatk1.0-0 \
 libatk1.0-dev \
 # Database libraries
 libmysqlclient-dev \
 libpq-dev \
 unixodbc-dev \
 # Other system libraries
 libpcsclite-dev \
 libpcsclite1 \
 libcups2 \
 libcups2-dev \
 libspeechd-dev \
 libsox-dev \
 libsox-fmt-all \
 libtbb-dev \
 libtbb2 \
 libnss3 \
 && \
 rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set environment variables for CUDA and cuDNN, nvidia runtime and path
ENV PATH=/usr/local/cuda/bin:/home/appuser/.local/bin:$PATH
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=$CUDA_HOME/bin:$PATH
ENV LD_LIBRARY_PATH=$VIRTUAL_ENV/.local/share/airunner/python/local/lib/python3.10/site-packages/PySide6/Qt/lib:/ususe_grr/lib/x86_64-linux-gnu:$CUDA_HOME/lib64:$CUDA_HOME/extras/CUPTI/lib64
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

RUN mkdir ~/.local/share/airunner && chown -R appuser:appuser ~/.local/share/airunner
COPY --chown=appuser:appuser . /app/
COPY ./package/prod/entrypoint.sh /home/appuser/entrypoint.sh
RUN chmod +x /home/appuser/entrypoint.sh
RUN curl https://pyenv.run | bash

# Download butler
WORKDIR /home/appuser/
RUN mkdir -p /home/appuser/butler && \
    cd /home/appuser/butler && \
    wget https://dl.itch.ovh/butler/linux-amd64/head/butler && chmod +x butler && \
    cd /home/appuser

RUN if ! grep -q "Pyenv configuration added by AI Runner" ~/.bashrc; then \
     cat << 'EOF' >> ~/.bashrc \
\
# Pyenv configuration added by AI Runner setup \
export PYENV_ROOT="$HOME/.pyenv" \
if [ -d "$PYENV_ROOT/bin" ]; then \
  export PATH="$PYENV_ROOT/bin:$PATH" \
fi \
if command -v pyenv &>/dev/null; then \
  eval "$(pyenv init - bash)" \
fi \
EOF \
   fi \
   && \
   # Check and add WSLg XDG_RUNTIME_DIR fix if not already present \
   if ! grep -q "WSLg XDG_RUNTIME_DIR Fix added by AI Runner" ~/.bashrc; then \
     cat << 'EOF' >> ~/.bashrc \
\
# WSLg XDG_RUNTIME_DIR Fix added by AI Runner setup \
if [ -n "$WSL_DISTRO_NAME" ]; then \
    if [ -d "/wslg/runtime-dir" ]; then \
        export XDG_RUNTIME_DIR="/wslg/runtime-dir" \
    elif [ -d "/mnt/wslg/runtime-dir" ]; then # Older WSLg path \
        export XDG_RUNTIME_DIR="/mnt/wslg/runtime-dir" \
    fi \
fi \
EOF \
   fi \
   && \
   # Check and add Qt environment variables for WSLg if not already present \
   if ! grep -q "Qt environment variables for WSLg added by AI Runner" ~/.bashrc; then \
     cat << 'EOF' >> ~/.bashrc \
\
# Qt environment variables for WSLg added by AI Runner setup \
if [ -n "$WSL_DISTRO_NAME" ]; then \
    export QT_QPA_PLATFORM=wayland \
    export QT_QPA_PLATFORMTHEME=gtk3 \
fi \
EOF \
   fi \
&& \
pyenv install 3.13.3 && \
pyenv global 3.13.3

COPY ./package/pip.conf /etc/pip.conf
RUN chown -R 1000:1000 /etc/pip.conf && \
    chmod 644 /etc/pip.conf

USER ${HOST_UID}:${HOST_GID}

WORKDIR /app

CMD ["/bin/bash"]
