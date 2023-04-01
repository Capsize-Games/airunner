FROM ubuntu:latest as base_image
USER root
ENV TZ=America/Denver
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && apt-get update \
    && apt-get upgrade -y \
    && apt install software-properties-common -y \
    && add-apt-repository ppa:ubuntu-toolchain-r/test \
    && apt-get update \
    && dpkg --add-architecture i386 \
    && apt-get update \
    && apt install libtinfo6 -y \
    && apt-get install -y git \
    && apt-get install -y wget \
    && apt-get install -y curl \
    && apt-get install -y vim \
    && apt-get install -y software-properties-common \
    && apt-get install -y gcc-9 \
    && apt-get install -y g++-9 \
    && apt-get install -y bash \
    && apt-get install -y build-essential \
    && apt-get install -y libssl-dev \
    && apt-get install -y libffi-dev \
    && apt-get install -y libgl1-mesa-dev \
    && apt-get install -y nvidia-cuda-toolkit \
    && apt-get install -y xclip \
    && apt-get install -y libjpeg-dev \
    && apt-get install -y zlib1g-dev \
    && apt-get install -y libpng-dev \
    && apt-get install software-properties-common -y \
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
    && rm -rf /var/lib/apt/lists/ \
    && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 60 --slave /usr/bin/g++ g++ /usr/bin/g++-9 \
    && rm -rf /var/lib/apt/lists/*

FROM base_image as cuda_install
USER root
WORKDIR /tmp
COPY libs/cuda_11.7.1_515.65.01_linux.run cuda_11.7.1_515.65.01_linux.run
RUN sh cuda_11.7.1_515.65.01_linux.run --silent --toolkit --toolkitpath=/usr/local/cuda-11.7 \
    && rm cuda_11.7.1_515.65.01_linux.run

FROM cuda_install as cudnn_install
WORKDIR /tmp
COPY libs/cudnn-linux-x86_64-8.6.0.163_cuda11-archive.tar.xz /tmp
RUN tar -xvf cudnn-linux-x86_64-8.6.0.163_cuda11-archive.tar.xz \
    && cp cudnn-*-archive/include/cudnn*.h /usr/local/cuda/include \
    && cp -P cudnn-*-archive/lib/libcudnn* /usr/local/cuda/lib64 \
    && chmod a+r /usr/local/cuda/include/cudnn*.h /usr/local/cuda/lib64/libcudnn* \
    && rm -rf cudnn-*-archive

FROM base_image as install_requirements
USER root
WORKDIR /app
ENV XFORMERS_MORE_DETAILS=1
RUN pip install nvidia-pyindex
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install --upgrade wheel
RUN pip install aihandler
RUN pip install accelerate

FROM install_requirements as add_user
RUN useradd -ms /bin/bash joe
USER root
WORKDIR /app

FROM add_user as fix_tcl
USER root
RUN ln -s /usr/share/tcltk/tcl8.6 /usr/share/tcltk/tcl8

FROM fix_tcl as install_apps
COPY build.sh build.sh
COPY build.py build.py
COPY build.airunner.linux.prod.spec build.airunner.linux.prod.spec
COPY linux.itch.toml linux.itch.toml
COPY src/airunner/src/icons src/airunner/src/icons
COPY src/airunner/pyqt src/airunner/pyqt
RUN python3 -c "from accelerate.utils import write_basic_config; write_basic_config(mixed_precision='fp16')"
RUN pip uninstall nvidia-cublas-cu11 -y

FROM install_apps as more_env
ENV PATH="/usr/local/lib/python3.10:/usr/local/lib/python3.10/bin:${PATH}"
ENV PYTHONPATH="/usr/local/lib/python3.10:/usr/local/lib/python3.10/bin:${PYTHONPATH}"
RUN pip install pyinstaller