FROM ubuntu:20.04 as base_image
# Base environment setup
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Denver
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

FROM base_image as wine_support
# Create a non-root user for Wine
RUN groupadd -g 1000 wineuser && \
    useradd -m -u 1000 -g 1000 -s /bin/bash wineuser && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        sudo \
        wget \
        gnupg2 \
        software-properties-common \
        coreutils \
        xvfb \
        cabextract \
        unzip \
        winbind \
        x11-apps && \
    # Add Wine repository key
    wget -nc https://dl.winehq.org/wine-builds/winehq.key && \
    dpkg --add-architecture i386 && \
    apt-key add winehq.key && \
    add-apt-repository 'deb https://dl.winehq.org/wine-builds/ubuntu/ focal main' && \
    apt-get update && \
    # Install wine - add both 32-bit and 64-bit components
    apt-get install -y --no-install-recommends \
        wine-stable \
        wine32 \
        wine64 \
        winetricks && \
    # Clean up
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    # Add wineuser to sudo without password
    echo "wineuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Wine environment variables - for the wineuser
ENV WINEDEBUG=fixme-all
ENV DISPLAY=:0
ENV WINEARCH=win64
ENV WINEPREFIX=/home/wineuser/.wine

# Switch to wineuser for wine operations
USER wineuser
WORKDIR /home/wineuser

# Initialize Wine prefix simply - skip problematic win10 setup
RUN mkdir -p ${WINEPREFIX} && \
    xvfb-run -a wine64 wineboot --init && \
    sleep 5 && \
    # Let Wine initialize properly
    xvfb-run -a wine64 cmd /c echo "Wine prefix initialized" && \
    # Skip winetricks win10, which is causing issues
    # Set Windows version to Windows 10 directly via registry
    xvfb-run -a wine64 reg add "HKEY_CURRENT_USER\\Software\\Wine\\Version" /v Windows /t REG_SZ /d win10 /f && \
    rm -rf /tmp/.X*-lock

# Install Python for Windows
ARG PYTHON_VERSION=3.10.11
ARG PYTHON_INSTALLER=python-${PYTHON_VERSION}-amd64.exe

RUN wget https://www.python.org/ftp/python/${PYTHON_VERSION}/${PYTHON_INSTALLER} && \
    xvfb-run -a wine64 ${PYTHON_INSTALLER} /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 TargetDir=C:\\Python310 && \
    rm ${PYTHON_INSTALLER} && \
    rm -rf /tmp/.X*-lock

# Install Wine Gecko - do this after Python
RUN wget https://dl.winehq.org/wine/wine-gecko/2.47.1/wine-gecko-2.47.1-x86_64.msi && \
    xvfb-run -a wine64 msiexec /i wine-gecko-2.47.1-x86_64.msi && \
    rm wine-gecko-2.47.1-x86_64.msi && \
    rm -rf /tmp/.X*-lock

# Set up PATH for Windows Python
ENV PATH="C:\\Python310;C:\\Python310\\Scripts;${PATH}"
ENV WINEPATH="C:\\Python310;C:\\Python310\\Scripts"

# Install pip, setuptools, wheel and PyInstaller
RUN xvfb-run -a wine64 C:\\Python310\\python.exe -m ensurepip --upgrade && \
    xvfb-run -a wine64 C:\\Python310\\python.exe -m pip install --upgrade pip setuptools wheel && \
    xvfb-run -a wine64 C:\\Python310\\python.exe -m pip install pyinstaller==6.12.0 && \
    rm -rf /tmp/.X*-lock

# Install UPX for binary compression
RUN wget https://github.com/upx/upx/releases/download/v4.0.2/upx-4.0.2-win64.zip && \
    unzip -o upx-4.0.2-win64.zip && \
    mkdir -p ${WINEPREFIX}/drive_c/Python310/Scripts/ && \
    cp upx-4.0.2-win64/upx.exe ${WINEPREFIX}/drive_c/Python310/Scripts/ && \
    rm -rf upx-4.0.2-win64 upx-4.0.2-win64.zip

# Set working directory to app (will be mounted from host)
WORKDIR /app

# Ensure app dir is accessible to wineuser
USER root
RUN mkdir -p /app && chown wineuser:wineuser /app

# Switch back to wineuser for any future operations
USER wineuser

# Set the entry point to be a helper script
COPY package/windows/entrypoint.sh /entrypoint.sh
USER root
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["xvfb-run", "-a", "wine64", "C:\\Python310\\python.exe"]