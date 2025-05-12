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
 # Wayland dependencies
 libwayland-client0 \
 libwayland-cursor0 \
 libwayland-egl1 \
 libwayland-server0 \
 wayland-protocols \
 libxkbcommon0 \
 # Keep minimal XCB for compatibility
 libxcb-cursor0 \
 libxcb-icccm4 \
 libxcb-image0 \
 libxcb-keysyms1 \
 libxcb-randr0 \
 libxcb-render-util0 \
 libxcb-xkb1 \
 libxkbcommon-x11-0 \
 # Database and other required libraries
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
 libegl1 \
 # Audio support
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

# Configure for Wayland by default
ENV QT_QPA_PLATFORM=wayland
ENV QT_WAYLAND_DISABLE_WINDOWDECORATION=1
ENV QT_QPA_PLATFORMTHEME=gtk3
ENV GDK_BACKEND=wayland
ENV XDG_SESSION_TYPE=wayland

# Create directory structure with correct permissions using UID:GID values
RUN mkdir -p /home/appuser/.local/share/airunner && chown -R ${HOST_UID}:${HOST_GID} /home/appuser/.local/share/airunner
COPY --chown=${HOST_UID}:${HOST_GID} . /app/
COPY ./package/prod/entrypoint.sh /home/appuser/entrypoint.sh
RUN chmod +x /home/appuser/entrypoint.sh

# Copy configuration files
COPY --chown=appuser:appgroup ./package/prod/qt_wayland_config.txt /tmp/qt_wayland_config.txt

# Install pyenv and Python as appuser
USER appuser
RUN echo "Installing pyenv as user $(whoami)" && \
    mkdir -p $HOME/.pyenv && \
    git clone --depth=1 https://github.com/pyenv/pyenv.git $HOME/.pyenv && \
    cd $HOME/.pyenv && \
    src/configure && \
    make -C src && \
    echo "Verifying pyenv installation..." && \
    echo "Directory listing of $HOME/.pyenv:" && \
    ls -la $HOME/.pyenv && \
    echo "Adding pyenv config to bashrc" && \
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> $HOME/.bashrc && \
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> $HOME/.bashrc && \
    echo 'eval "$(pyenv init --path)"' >> $HOME/.bashrc && \
    echo 'eval "$(pyenv init -)"' >> $HOME/.bashrc && \
    echo "Adding Qt Wayland config to bashrc" && \
    cat /tmp/qt_wayland_config.txt >> $HOME/.bashrc && \
    echo "Installing Python with pyenv" && \
    export PYENV_ROOT="$HOME/.pyenv" && \
    export PATH="$PYENV_ROOT/bin:$PATH" && \
    if [ -f "$HOME/.pyenv/bin/pyenv" ]; then \
        echo "Using bin/pyenv" && \
        $HOME/.pyenv/bin/pyenv install 3.13.3 && \
        $HOME/.pyenv/bin/pyenv global 3.13.3; \
    elif [ -f "$HOME/.pyenv/libexec/pyenv" ]; then \
        echo "Using libexec/pyenv" && \
        $HOME/.pyenv/libexec/pyenv install 3.13.3 && \
        $HOME/.pyenv/libexec/pyenv global 3.13.3; \
    else \
        echo "ERROR: pyenv executable not found"; \
        exit 1; \
    fi

USER root
COPY ./package/pip.conf /etc/pip.conf
RUN chown -R ${HOST_UID}:${HOST_GID} /etc/pip.conf && \
    chmod 644 /etc/pip.conf

USER ${HOST_UID}:${HOST_GID}

WORKDIR /app

# Set default shell to bash
SHELL ["/bin/bash", "-c"]
ENTRYPOINT ["/bin/bash", "/home/appuser/entrypoint.sh"]
CMD ["/bin/bash"]
