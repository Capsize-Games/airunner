[![Banner](banner.png)](https://capsizegames.itch.io/ai-runner)
[![Windows Build](https://github.com/Capsize-Games/airunner/actions/workflows/repository-dispatch-windows.yml/badge.svg)](https://github.com/Capsize-Games/airunner/actions/workflows/repository-dispatch-windows.yml)
[![Run airunner on Linux](https://github.com/Capsize-Games/airunner/actions/workflows/repository-dispatch.yml/badge.svg)](https://github.com/Capsize-Games/airunner/actions/workflows/repository-dispatch.yml)
[![Upload Python Package](https://github.com/Capsize-Games/airunner/actions/workflows/python-publish.yml/badge.svg)](https://github.com/Capsize-Games/airunner/actions/workflows/python-publish.yml)
[![Discord](https://img.shields.io/discord/839511291466219541?color=5865F2&logo=discord&logoColor=white)](https://discord.gg/PUVDDCJ7gz)
![GitHub](https://img.shields.io/github/license/Capsize-Games/airunner)
![GitHub last commit](https://img.shields.io/github/last-commit/Capsize-Games/airunner)
![GitHub issues](https://img.shields.io/github/issues/Capsize-Games/airunner)
![GitHub closed issues](https://img.shields.io/github/issues-closed/Capsize-Games/airunner)
![GitHub pull requests](https://img.shields.io/github/issues-pr/Capsize-Games/airunner)
![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed/Capsize-Games/airunner)

AI Runner allows you to run Stable Diffusion locally using your own hardware. It comes with drawing tools and an infinite canvas which lets you outpaint to any size you wish.


![img.png](img.png)


## [Download the official build on itch.io](https://capsizegames.itch.io/ai-runner)!

This is the compiled version of AI Runner which you can use without installing any additional dependencies.

---

## Development installation

**Prerequisites**

- Ubuntu 20.04+ or Windows 10+
- Python 3.10.6
- pip-23.0.1

---

### Docker

[Current builds of AI Runner are compiled with pyinstaller on docker.](https://github.com/Capsize-Games/airunner/pkgs/container/airunner%2Fairunner)

**Pull Docker container from repo**

Linux
```
docker pull ghcr.io/capsize-games/airunner/airunner:linux
```

Windows
```
docker pull ghcr.io/capsize-games/airunner/airunner:windows
```

**Build Docker**

Linux
```
docker-compose -f docker-compose.yml build
docker tag ghcr.io/capsize-games/airunner/airunner:linux ghcr.io/capsize-games/airunner/airunner:linux
docker push ghcr.io/capsize-games/airunner/airunner:linux
```

Windows
```
docker-compose -f docker-compose.windows.yml build
docker tag ghcr.io/capsize-games/airunner/airunner:windows ghcr.io/capsize-games/airunner/airunner:windows
docker push ghcr.io/capsize-games/airunner/airunner:windows
```

**Run the app using Docker**
```
docker-compose run linux python3 /app/main.py
```

**Build latest version** of AI Runner using Docker locally - this will output a `build` and `dist` folder on your machine.
```
linux
docker run -it -e DEV_ENV=0 -e AIRUNNER_ENVIRONMENT=prod -e AIRUNNER_OS=linux -e PYTORCH_CUDA_ALLOC_CONF=garbage_collection_threshold:0.9,max_split_size_mb:512 -e NUMBA_CACHE_DIR=/tmp/numba_cache -e DISABLE_TELEMETRY=1 -e TCL_LIBDIR_PATH=/usr/lib/x86_64-linux-gnu/ -e TK_LIBDIR_PATH=/usr/lib/x86_64-linux-gnu/ -v $(pwd)/build:/app/build -v $(pwd)/dist:/app/dist -v $(pwd)/../diffusers:/app/diffusers ghcr.io/capsize-games/airunner/airunner:linux bash build.sh

windows
docker run -it -e DEV_ENV=0 -e AIRUNNER_ENVIRONMENT=prod -e AIRUNNER_OS=windows -e PYTORCH_CUDA_ALLOC_CONF=garbage_collection_threshold:0.9,max_split_size_mb:512 -e NUMBA_CACHE_DIR=/tmp/numba_cache -e DISABLE_TELEMETRY=1 -v $(pwd)/build:/app/build -v $(pwd)/dist:/app/dist -v $(pwd)/../diffusers:/app/diffusers ghcr.io/capsize-games/airunner/airunner:windows wine64 build.windows.cmd
docker run --rm -m 24g --cpus=12 -v $(pwd)/dist:/app/dist -v $(pwd)/build:/app/build ghcr.io/capsize-games/airunner/airunner:windows bash build.windows.sh
```
Run it with `./dist/airunner/airunner`

### Pypi installation

If you would like to use AI Runner as a library, follow this method of installation.
Currently there isn't much of an external API so using AI Runner as a library is not recommended.

#### Windows
```
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu117
pip install airunner
pip install https://github.com/w4ffl35/diffusers/archive/refs/tags/v0.15.0.ckpt_fix_0.0.1.tar.gz
pip install https://github.com/acpopescu/bitsandbytes/releases/download/v0.38.0-win0/bitsandbytes-0.38.1-py3-none-any.whl
```

#### Linux
```
pip install torch torchvision torchaudio bitsandbytes triton==2.0.0
pip install airunner
pip install https://github.com/w4ffl35/diffusers/archive/refs/tags/v0.15.0.ckpt_fix_0.0.1.tar.gz --no-deps
```

---

### Source

#### Windows

Install required libraries
```
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu117
```

Clone handler
```
git clone -b develop-windows https://github.com/Capsize-Games/aihandler.git
cd aihandler && pip install -e .
```

Clone AI Runner
```
git clone -b develop https://github.com/Capsize-Games/airunner.git
cd airunner && pip install -e .
```

Install dependencies
```
pip install https://github.com/w4ffl35/diffusers/archive/refs/tags/v0.15.0.ckpt_fix_0.0.1.tar.gz --no-deps
pip install https://github.com/acpopescu/bitsandbytes/releases/download/v0.37.2-win.0/bitsandbytes-0.37.2-py3-none-any.whl
```

Run
```
python airunner/src/airunner/main.py
```

#### Linux

Clone handler and install
```
git clone develop https://github.com/Capsize-Games/aihandler.git
cd aihandler && pip install -e .
```

Clone AI Runner
```
git clone -b develop https://github.com/Capsize-Games/aihandler.git
```

---

### Txt2video support

#### Linux

Install the codecs `sudo apt-get install ubuntu-restricted-extras`

---

## Using AI Runner

Instructions on how to setup and use AI Runner [can be found in the wiki](https://github.com/Capsize-Games/airunner/wiki/AI-Runner)