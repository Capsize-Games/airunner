FROM ubuntu:22.04 as base_image
USER root
ENV TZ=America/Denver
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
#    && apt-get install -y nvidia-cuda-toolkit \
    && apt-get install -y xclip \
    && apt-get install -y libjpeg-dev \
    && apt-get install -y zlib1g-dev \
    && apt-get install -y libpng-dev \
    && apt-get install patchelf -y \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt update \
    && apt install python3.10 -y \
    && apt install python3.10-distutils -y \
    && apt install python3-pip -y \
    && apt install python3.10-tk -y \
    && apt install -y upx \
    && apt-get install patchelf -y \
    && apt-get install ccache -y \
    && apt-get install -y libxcb-xinerama0 \
#    && apt-get install -y libgtk-3-0 \
    && apt-get install qt6-qpa-plugins -y \
    && apt-get install libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libxcb-xinerama0 -y \
    && apt-get install -y qt6-base-dev \
    && apt-get install -y gstreamer1.0-gl \
    && rm -rf /var/lib/apt/lists/ \
    && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 60 --slave /usr/bin/g++ g++ /usr/bin/g++-9 \
    && rm -rf /var/lib/apt/lists/*

FROM base_image as install_requirements
USER root
WORKDIR /app
RUN pip install nvidia-pyindex
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install --upgrade wheel
RUN pip install requests cmake
RUN pip install torch torchvision torchaudio

FROM install_requirements as fix_tcl
USER root
RUN ln -s /usr/share/tcltk/tcl8.6 /usr/share/tcltk/tcl8

FROM fix_tcl as more_env
WORKDIR /app
ENV PATH="/usr/local/lib/python3.10:/usr/local/lib/python3.10/bin:${PATH}"
ENV PYTHONPATH="/usr/local/lib/python3.10:/usr/local/lib/python3.10/bin:${PYTHONPATH}"
RUN pip install pyinstaller

FROM more_env as build_files
WORKDIR /app
COPY dobuild.py dobuild.py
COPY build.sh build.sh
COPY build.airunner.linux.prod.spec build.airunner.linux.prod.spec
COPY setup.py setup.py