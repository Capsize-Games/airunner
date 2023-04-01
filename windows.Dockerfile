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
    && rm -rf /var/lib/apt/lists/ \
    && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 60 --slave /usr/bin/g++ g++ /usr/bin/g++-9

FROM base_image as wine_support
ENV WINEDEBUG=fixme-all
ENV DISPLAY=:0
ENV WINEARCH=win64
ENV WINEPREFIX=/home/.wine-win10
RUN apt-get update
COPY lib/winehq.key winehq.key
RUN apt-key add winehq.key \
    && add-apt-repository 'deb https://dl.winehq.org/wine-builds/ubuntu/ focal main' \
    && apt-get update \
    && apt-get install -y coreutils \
    && apt-get install -y winbind \
    && apt-get install -y xvfb \
    && apt-get install -y winehq-stable \
    && apt-get install -y winetricks \
    && apt-get install -y x11-apps \
    && apt-get install -y wine64 \
    && apt-get install -y wine32 \
    && apt-get install -y winbind \
    && apt-get install -y cabextract \
    && winetricks win10

FROM wine_support as winegecko
COPY lib/wine-gecko-2.47.1-x86_64.msi wine-gecko-2.47.1-x86_64.msi
RUN wine64 msiexec /i wine-gecko-2.47.1-x86_64.msi \
    && rm wine-gecko-2.47.1-x86_64.msi

FROM winegecko as install_python
COPY lib/python-3.10.8-amd64.exe python-3.10.8-amd64.exe
RUN xvfb-run -e /dev/stdout wine64 python-3.10.8-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 TargetDir=C:\\Python310 \
    && rm python-3.10.8-amd64.exe \
    && rm -rf /tmp/.X99-lock

FROM install_python as install_git
COPY lib/PortableGit PortableGit
RUN cp -r PortableGit /home/.wine-win10/drive_c/PortableGit \
    && wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\\;C:\\PortableGit;C:\\Program Files\\NVIDIA\\CUDNN\\v8.6.0.163\\bin;C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v11.7\\bin;C:\\Python310;C:\\Python310\\site-packages;C:\\Python310\\site-packages\\lib;%PATH%" /f

FROM install_git as add_user
RUN useradd -ms /bin/bash joe
USER root
WORKDIR /app

FROM add_user as final
USER root
RUN wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages;%PATH%" \
    && wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\Pillow.libs;%PATH%" \
    && wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\tokenizers.libs;%PATH%" \
    && wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\xformers\triton;%PATH%" \
    && wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\nvidia\cuda_runtime\lib\;%PATH%" \
    && wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\nvidia\cudnn\lib;%PATH%" \
    && wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\numpy.libs;%PATH%" \
    && wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\h5py.libs;%PATH%" \
    && wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\torchaudio\lib\;%PATH%" \
    && wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\torch\lib;%PATH%" \
    && wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\torch\bin;%PATH%" \
    && wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\torch\_C;%PATH%" \
    && wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\torch;%PATH%" \
    && wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\triton;%PATH%" \
    && wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\triton/_C;%PATH%" \
    && wine64 reg add "HKEY_CURRENT_USER\Environment" /v LD_LIBRARY_PATH /t REG_EXPAND_SZ /d "%PATH%;%LD_LIBRARY_PATH%" /f

FROM final as install_apps
WORKDIR /app
USER root
ENV DISPLAY=:0
RUN apt-get install -y mesa-utils \
    && apt-get install -y libgl1-mesa-glx \
    && wine64 C:\\Python310\\python.exe -m pip install pyinstaller \
    && wine64 C:\\Python310\\python.exe -m pip install torch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1 --index-url https://download.pytorch.org/whl/cu117 \
    && wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\\;Z:\\app\\lib\\PortableGit\\cmd;C:\\Program Files\\NVIDIA\\CUDNN\\v8.6.0.163\\bin;C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v11.7\\bin;C:\\Python310;C:\\Python310\\site-packages;C:\\Python310\\site-packages\\lib;%PATH%" /f \
    && apt install git \
    && chown joe:joe /home/.wine-win10 \
    && mkdir -p joe:joe /home/.wine-win10/drive_c/users/joe && chown -R joe:joe joe:joe /home/.wine-win10/drive_c/users/joe \
    && chown -R joe:joe /home/.wine-win10/drive_c/users/root \
    && mkdir -p /app/.cache/mesa_shader_cache && chown -R root:root /app/.cache/mesa_shader_cache \
    && mkdir -p /home/.wine-win10/drive_c/users/joe/AppData/Roaming && chown -R joe:joe /home/.wine-win10/drive_c/users/joe/AppData/Roaming \
    && mkdir -p /home/.wine-win10/drive_c/users/joe/AppData/Local && chown -R joe:joe /home/.wine-win10/drive_c/users/joe/AppData/Local