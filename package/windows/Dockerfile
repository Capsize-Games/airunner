FROM ubuntu:22.04

ARG PYTHON_VERSION=3.10.11
ARG PYTHON_INSTALLER=python-3.10.11.exe
ARG WINE_USER=wineuser
ARG WINE_UID=1000
ARG WINE_GID=1000

ENV DEBIAN_FRONTEND=noninteractive
ENV WINEDEBUG=-all
ENV WINEPREFIX=/home/${WINE_USER}/.wine
ENV WINEARCH=win64
ENV PATH="${WINEPREFIX}/drive_c/Python310:${WINEPREFIX}/drive_c/Python310/Scripts:${PATH}"

# Install prerequisites including Wine
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        ca-certificates \
        cabextract \
        gnupg \
        software-properties-common \
        winbind \
        xvfb \
        winehq-stable \
        wine-stable \
        wine-stable-i386 \
        wine-stable-amd64 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user for Wine
RUN groupadd --gid ${WINE_GID} ${WINE_USER} && \
    useradd --uid ${WINE_UID} --gid ${WINE_GID} --create-home --shell /bin/bash ${WINE_USER}

USER ${WINE_USER}
WORKDIR /home/${WINE_USER}

# Set up Wine prefix
RUN winecfg

# Download and install Python for Windows
RUN wget https://www.python.org/ftp/python/${PYTHON_VERSION}/${PYTHON_INSTALLER} && \
    wine ${PYTHON_INSTALLER} /quiet InstallAllUsers=0 PrependPath=1 TargetDir=C:\Python310 && \
    rm ${PYTHON_INSTALLER}

# Install pip and setuptools within Wine
RUN wine python -m ensurepip --upgrade && \
    wine python -m pip install --upgrade pip setuptools wheel

# Install PyInstaller within Wine
RUN wine pip install pyinstaller==6.12.0

WORKDIR /app

# Set entrypoint for running commands in Wine
COPY package/windows/entrypoint.sh /entrypoint.sh
RUN sudo chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["wine", "python"]
