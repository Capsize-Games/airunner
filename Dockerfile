FROM ubuntu:22.04 as base_image
USER root
ENV TZ=America/Denver
ENV HOME=/app
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && apt-get update \
    && apt-get upgrade -y \
    && apt install software-properties-common -y \
    && add-apt-repository ppa:ubuntu-toolchain-r/test \
    && apt-get update \
    && apt install libtinfo6 -y \
    && apt-get install -y git \
    && apt-get install -y wget \
    && apt-get install -y software-properties-common \
    && apt-get install -y gcc-9 \
    && apt-get install -y g++-9 \
    && apt-get install -y bash \
    && apt-get install -y build-essential \
    && apt-get install -y libssl-dev \
    && apt-get install -y libffi-dev \
    && apt-get install -y libgl1-mesa-dev \
    && apt-get install -y fonts-noto-color-emoji \
    && apt-get install -y libportaudio2 \
    && apt-get install -y libxcb-cursor0 \
    && apt-get install -y espeak \
    && apt-get install -y xclip \
    && apt-get install -y libjpeg-dev \
    && apt-get install -y zlib1g-dev \
    && apt-get install -y libpng-dev \
    && apt-get install -y patchelf \
    && apt-get install -y ccache \
    && apt-get install -y libxcb-xinerama0 \
    && apt-get install -y gstreamer1.0-gl \
    && apt-get install -y cmake \
    && apt-get install -y ninja-build \
    && apt-get install -y python3 \
    && apt-get install -y python3-pip \
    && apt-get install -y python3.10 \
    && apt-get install -y python3.10-distutils \
    && apt-get install -y python3.10-tk \
    && apt-get install -y upx \
    && apt-get install -y libgl1-mesa-glx \
    && apt-get install -y libglib2.0-0 \
    && apt-get install -y libsm6 \
    && apt-get install -y libxext6 \
    && apt-get install -y libxrender-dev \
    && ln -s /usr/share/tcltk/tcl8.6 /usr/share/tcltk/tcl8 \
    && rm -rf /var/lib/apt/lists/ \
    && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 60 --slave /usr/bin/g++ g++ /usr/bin/g++-9 \
    && rm -rf /var/lib/apt/lists/*

FROM base_image as download_qt
USER root
ENV TZ=America/Denver
ENV HOME=/app
RUN wget https://download.qt.io/archive/qt/6.7/6.7.0/single/qt-everywhere-src-6.7.0.tar.xz

FROM download_qt as build_qt
USER root
ENV TZ=America/Denver
ENV HOME=/app
RUN tar -xf qt-everywhere-src-6.7.0.tar.xz \
    && cd qt-everywhere-src-6.7.0 \
    && cmake -G Ninja -B build -DCMAKE_INSTALL_PREFIX=/usr/local/qt6 \
    && cmake --build build --parallel

FROM build_qt as install_qt
USER root
ENV TZ=America/Denver
ENV HOME=/app
RUN cd qt-everywhere-src-6.7.0/build \
    && if [ -f cmake_install.cmake ]; then cmake --install .; else echo "cmake_install.cmake not found"; exit 1; fi \
    && cd ../.. \
    && rm -rf qt-everywhere-src-6.7.0 qt-everywhere-src-6.7.0.tar.xz

FROM install_qt as create_user
RUN useradd -ms /bin/bash appuser \
    && chown -R appuser:appuser /app \
    && apt-get update \
    && apt-get install -y libxkbcommon-x11-0 \
    && rm -rf /var/lib/apt/lists/*

USER appuser
WORKDIR /app
ENV HOME=/app
ENV PATH="/home/appuser/.local/bin:${PATH}"
ENV PYTHONUSERBASE=/home/appuser/.local

ENV PATH="/usr/local/qt6/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/qt6/lib:${LD_LIBRARY_PATH}"

FROM create_user as install_requirements
USER appuser
WORKDIR /app
ENV HOME=/app
ENV PATH="/home/appuser/.local/bin:${PATH}"
ENV PYTHONUSERBASE=/home/appuser/.local
RUN pip install nvidia-pyindex
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install --upgrade wheel
RUN pip install requests aihandler cmake
RUN pip uninstall torch torchvision -y
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118 --upgrade

FROM install_requirements as install_apps
USER appuser
WORKDIR /app
ENV HOME=/app
ENV PATH="/home/appuser/.local/bin:${PATH}"
ENV PYTHONUSERBASE=/home/appuser/.local
RUN python3 -c "from accelerate.utils import write_basic_config; write_basic_config(mixed_precision='fp16')"
RUN pip uninstall nvidia-cublas-cu11 nvidia-cublas-cu12 -y
RUN pip uninstall xformers -y

FROM install_apps as more_env
USER appuser
WORKDIR /app
ENV HOME=/app
ENV PATH="/home/appuser/.local/bin:${PATH}"
ENV PYTHONUSERBASE=/home/appuser/.local
RUN pip install pyinstaller

FROM more_env as build_files
USER appuser
WORKDIR /app
ENV HOME=/app
ENV PATH="/home/appuser/.local/bin:${PATH}"
ENV PYTHONUSERBASE=/home/appuser/.local
COPY dobuild.py dobuild.py
COPY build.sh build.sh
COPY setup.py setup.py

FROM build_files as build_airunner
USER appuser
WORKDIR /app
ENV HOME=/app
ENV PATH="/home/appuser/.local/bin:${PATH}"
ENV PYTHONUSERBASE=/home/appuser/.local
RUN git clone https://github.com/Capsize-Games/airunner.git /app/airunner \
    && cd /app/airunner \
    && git checkout master \
    && git pull \
    && python3 -m pip install .

FROM build_airunner as build_airunner_executable
USER appuser
WORKDIR /app
ENV HOME=/app
ENV PATH="/home/appuser/.local/bin:${PATH}"
ENV PYTHONUSERBASE=/home/appuser/.local
COPY build.airunner.linux.prod.spec build.airunner.linux.prod.spec
