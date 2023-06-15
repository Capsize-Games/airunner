FROM ubuntu:22.04 as base_image
USER root
ENV TZ=America/Denver
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && apt update \
    && apt upgrade -y \
    && apt install software-properties-common -y \
    && add-apt-repository ppa:ubuntu-toolchain-r/test \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt update \
    && apt install libtinfo6 -y \
    && apt install -y git \
    && apt install -y wget \
    && apt install -y curl \
    && apt install -y vim \
    && apt install -y software-properties-common \
    && apt install -y gcc-9 \
    && apt install -y g++-9 \
    && apt install -y bash \
    && apt install -y build-essential \
    && apt install -y libssl-dev \
    && apt install -y libffi-dev \
    && apt install -y libgl1-mesa-dev \
    && apt install -y xclip \
    && apt install -y libjpeg-dev \
    && apt install -y zlib1g-dev \
    && apt install -y libpng-dev \
    && apt install patchelf -y \
    && apt install python3.10 -y \
    && apt install python3.10-distutils -y \
    && apt install python3-pip -y \
    && apt install python3.10-tk -y \
    && apt install -y upx \
    && apt install patchelf -y \
    && apt install ccache -y \
    && apt install -y libxcb-xinerama0 \
    && apt install -y libgtk-3-0 \
    && apt install libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libxcb-xinerama0 -y \
    && apt install -y gstreamer1.0-gl \
    && apt install -y nvidia-cuda-toolkit \
    && rm -rf /var/lib/apt/lists/ \
    && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 60 --slave /usr/bin/g++ g++ /usr/bin/g++-9 \
    && rm -rf /var/lib/apt/lists/*

FROM base_image as install_requirements
USER root
WORKDIR /app
ENV XFORMERS_MORE_DETAILS=1
RUN pip install nvidia-pyindex
WORKDIR /app
RUN pip install --upgrade pip \
    && pip install --upgrade setuptools \
    && pip install --upgrade wheel \
    && pip install bitsandbytes accelerate requests aihandler cmake \
    && pip install triton

FROM install_requirements as fix_tcl
USER root
RUN ln -s /usr/share/tcltk/tcl8.6 /usr/share/tcltk/tcl8

FROM fix_tcl as install_apps
RUN python3 -c "from accelerate.utils import write_basic_config; write_basic_config(mixed_precision='fp16')"

FROM install_apps as more_env
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