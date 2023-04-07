FROM ubuntu:latest as base_image
USER root
ENV TZ=America/Denver
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get update
RUN apt-get upgrade -y
RUN apt install software-properties-common -y
RUN add-apt-repository ppa:ubuntu-toolchain-r/test
RUN apt-get update
RUN dpkg --add-architecture i386
RUN apt-get update
RUN apt install libtinfo6 -y
RUN apt-get install -y git
RUN apt-get install -y wget
RUN apt-get install -y curl
RUN apt-get install -y vim
RUN apt-get install -y software-properties-common
RUN apt-get install -y gcc-9
RUN apt-get install -y g++-9
RUN apt-get install -y bash
RUN apt-get install -y build-essential
RUN apt-get install -y libssl-dev
RUN apt-get install -y libffi-dev
RUN apt-get install -y libgl1-mesa-dev
RUN apt-get install -y nvidia-cuda-toolkit
RUN apt-get install -y xclip
RUN apt-get install -y libjpeg-dev
RUN apt-get install -y zlib1g-dev
RUN apt-get install -y libpng-dev
RUN rm -rf /var/lib/apt/lists/
RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 60 --slave /usr/bin/g++ g++ /usr/bin/g++-9

FROM base_image as wine_support
ENV WINEDEBUG=fixme-all
ENV DISPLAY=:0
ENV WINEARCH=win64
ENV WINEPREFIX=/home/.wine-win10
RUN apt-get update
RUN wget -nc https://dl.winehq.org/wine-builds/winehq.key
RUN apt-key add winehq.key
RUN add-apt-repository 'deb https://dl.winehq.org/wine-builds/ubuntu/ focal main'
RUN apt-get update
RUN apt-get install -y coreutils
RUN apt-get install -y winbind
RUN apt-get install -y xvfb
RUN apt-get install -y winehq-stable
RUN apt-get install -y winetricks
RUN apt-get install -y x11-apps
RUN apt-get install -y wine64
RUN apt-get install -y wine32
RUN apt-get install -y winbind
RUN apt-get install -y cabextract
RUN winetricks win10

FROM wine_support as winegecko
RUN wget https://dl.winehq.org/wine/wine-gecko/2.47.1/wine-gecko-2.47.1-x86_64.msi
RUN wine64 msiexec /i wine-gecko-2.47.1-x86_64.msi
RUN rm wine-gecko-2.47.1-x86_64.msi

FROM winegecko as install_python
RUN wget https://www.python.org/ftp/python/3.10.8/python-3.10.8-amd64.exe
RUN xvfb-run -e /dev/stdout wine64 python-3.10.8-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 TargetDir=C:\\Python310
RUN rm python-3.10.8-amd64.exe
RUN rm -rf /tmp/.X99-lock

FROM install_python as install_git
RUN apt-get install -y unzip
RUN wget https://github.com/git-for-windows/git/releases/download/v2.40.0.windows.1/MinGit-2.40.0-64-bit.zip -O MinGit-2.40.0-64-bit.zip
RUN unzip -o MinGit-2.40.0-64-bit.zip
RUN rm MinGit-2.40.0-64-bit.zip

FROM install_git as final
USER root
RUN wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages;%PATH%"
RUN wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\Pillow.libs;%PATH%"
RUN wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\tokenizers.libs;%PATH%"
RUN wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\xformers\triton;%PATH%"
RUN wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\nvidia\cuda_runtime\lib\;%PATH%"
RUN wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\nvidia\cudnn\lib;%PATH%"
RUN wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\numpy.libs;%PATH%"
RUN wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\h5py.libs;%PATH%"
RUN wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\torchaudio\lib\;%PATH%"
RUN wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\torch\lib;%PATH%"
RUN wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\torch\bin;%PATH%"
RUN wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\torch\_C;%PATH%"
RUN wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\torch;%PATH%"
RUN wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\triton;%PATH%"
RUN wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\Python310\site-packages\triton/_C;%PATH%"
RUN wine64 reg add "HKEY_CURRENT_USER\Environment" /v LD_LIBRARY_PATH /t REG_EXPAND_SZ /d "%PATH%;%LD_LIBRARY_PATH%" /f

FROM final as install_apps
WORKDIR /app
USER root
ENV DISPLAY=:0
RUN apt-get install -y mesa-utils
RUN apt-get install -y libgl1-mesa-glx
RUN wine64 C:\\Python310\\python.exe -m pip install --upgrade pyinstaller
RUN wine64 C:\\Python310\\python.exe -m pip install torch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1 --index-url https://download.pytorch.org/whl/cu117
RUN wine64 reg add "HKEY_CURRENT_USER\Environment" /v PATH /t REG_EXPAND_SZ /d "C:\\;Z:\\app\\lib\\PortableGit\\cmd;C:\\Program Files\\NVIDIA\\CUDNN\\v8.6.0.163\\bin;C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v11.7\\bin;C:\\Python310;C:\\Python310\\site-packages;C:\\Python310\\site-packages\\lib;%PATH%" /f
RUN apt install git
RUN chown root:root /home/.wine-win10
RUN mkdir -p root:root /home/.wine-win10/drive_c/users/root && chown -R root:root root:root /home/.wine-win10/drive_c/users/root
RUN chown -R root:root /home/.wine-win10/drive_c/users/root
RUN mkdir -p /app/.cache/mesa_shader_cache && chown -R root:root /app/.cache/mesa_shader_cache
RUN mkdir -p /home/.wine-win10/drive_c/users/root/AppData/Roaming && chown -R root:root /home/.wine-win10/drive_c/users/root/AppData/Roaming
RUN mkdir -p /home/.wine-win10/drive_c/users/root/AppData/Local && chown -R root:root /home/.wine-win10/drive_c/users/root/AppData/Local

FROM install_apps as install_upx
RUN wget https://github.com/upx/upx/releases/download/v4.0.2/upx-4.0.2-win64.zip
RUN unzip -o upx-4.0.2-win64.zip
RUN cp upx-4.0.2-win64/upx.exe /home/.wine-win10/drive_c/Python310/Scripts/

FROM install_upx as install_libs
USER root
RUN wine64 C:\\Python310\\python.exe -m pip install torch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1 --index-url https://download.pytorch.org/whl/cu117
RUN wine64 C:\\Python310\\python.exe -m pip install https://github.com/w4ffl35/diffusers/archive/refs/tags/v0.14.0.ckpt_fix.tar.gz
RUN wine64 C:\\Python310\\python.exe -m pip install https://github.com/w4ffl35/transformers/archive/refs/tags/tensor_fix-v1.0.2.tar.gz
RUN wine64 C:\\Python310\\python.exe -m pip install https://github.com/acpopescu/bitsandbytes/releases/download/v0.37.2-win.0/bitsandbytes-0.37.2-py3-none-any.whl
RUN wine64 C:\\Python310\\python.exe -m pip install aihandlerwindows
RUN wine64 C:\\Python310\\python.exe -c "from accelerate.utils import write_basic_config; write_basic_config(mixed_precision='fp16')"

FROM install_libs as source_files
COPY build.windows.sh /app/build.windows.sh
COPY build.windows.py /app/build.windows.py
COPY build.airunner.windows.prod.spec /app/build.airunner.windows.prod.spec
COPY windows.itch.toml /app/windows.itch.toml
COPY src/airunner/v1.yaml /app/v1.yaml
COPY src/airunner/v2.yaml /app/v2.yaml
COPY src/airunner/src/icons /app/src/airunner/src/icons
COPY src/airunner/pyqt /app/src/airunner/pyqt
RUN cp /usr/lib/x86_64-linux-gnu/wine/api-ms-win-shcore-scaling-l1-1-1.dll /home/.wine-win10/drive_c/api-ms-win-shcore-scaling-l1-1-1.dll

FROM source_files as precompile_hooks
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\_pyinstaller_hooks_contrib\\hooks\\stdhooks\\hook-cv2.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\Lib\\site-packages\\numpy\\_pyinstaller\\hook-numpy.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\hook-multiprocessing.util.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\hook-xml.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\hook-platform.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\hook-sysconfig.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\hook-xml.etree.cElementTree.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\_pyinstaller_hooks_contrib\\hooks\\stdhooks\\hook-torch.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\hook-packaging.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\hook-pkg_resources.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module\\hook-six.moves.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\hook-scipy.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\hook-scipy.sparse.csgraph.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\hook-scipy.linalg.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\hook-sqlite3.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\hook-scipy.spatial.transform.rotation.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\hook-PIL.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\hook-PIL.Image.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\hook-PIL.ImageFilter.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\hook-xml.dom.domreg.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module\\hook-urllib3.packages.six.moves.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\_pyinstaller_hooks_contrib\\hooks\\stdhooks\\hook-charset_normalizer.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\_pyinstaller_hooks_contrib\\hooks\\stdhooks\\hook-certifi.py
#RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\hook-pygments.py
#RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\PyInstaller\\hooks\\hook-importlib_metadata.py
RUN wine64 C:\\Python310\\python.exe -m py_compile C:\\Python310\\lib\\site-packages\\_pyinstaller_hooks_contrib\\hooks\\pre_safe_import_module\\hook-tensorflow.py
