FROM ubuntu:20.04 as base_image
USER root
ENV TZ=America/Denver
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && apt update \
    && apt upgrade -y \
    && apt install software-properties-common -y \
    && add-apt-repository ppa:ubuntu-toolchain-r/test \
    && apt update \
    && apt install -y libtinfo6 \
    && apt install -y git \
    && apt install -y wget \
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
    && apt install -y patchelf \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt update \
    && apt install -y python3.10 \
    && apt install -y python3.10-distutils \
    && apt install -y python3-pip \
    && apt install -y python3.10-tk \
    && apt install -y upx \
    && apt install -y patchelf \
    && apt install -y ccache \
    && apt install -y libxcb-xinerama0 \
    && apt install -y libgtk-3-0 \
    && apt install -y libgl1-mesa-glx \
    && apt install -y libglib2.0-0 \
    && apt install -y libsm6 \
    && apt install -y libxext6 \
    && apt install -y libxrender-dev \
    && apt install -y libxcb-xinerama0 \
    && apt install -y gstreamer1.0-gl \
    && apt install -y nvidia-cuda-toolkit \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/ \
    && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 60 --slave /usr/bin/g++ g++ /usr/bin/g++-9 \
    && rm -rf /var/lib/apt/lists/*

FROM base_image as install_requirements
USER root
WORKDIR /app
ENV XFORMERS_MORE_DETAILS=1
RUN pip install nvidia-pyindex
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install --upgrade wheel
RUN pip install bitsandbytes
RUN pip install accelerate
RUN pip install requests
RUN pip install aihandler
RUN pip install cmake
RUN pip install triton

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