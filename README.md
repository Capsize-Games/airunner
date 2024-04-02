[![Banner](banner.png)](https://capsizegames.itch.io/ai-runner)
[![Discord](https://img.shields.io/discord/839511291466219541?color=5865F2&logo=discord&logoColor=white)](https://discord.gg/PUVDDCJ7gz)
[![Windows Build](https://github.com/Capsize-Games/airunner/actions/workflows/windows-dispatch.yml/badge.svg)](https://github.com/Capsize-Games/airunner/actions/workflows/windows-dispatch.yml)
[![Linux Build](https://github.com/Capsize-Games/airunner/actions/workflows/linux-dispatch.yml/badge.svg)](https://github.com/Capsize-Games/airunner/actions/workflows/linux-dispatch.yml)
[![PyPi](https://github.com/Capsize-Games/airunner/actions/workflows/pypi-dispatch.yml/badge.svg)](https://github.com/Capsize-Games/airunner/actions/workflows/pypi-dispatch.yml)
![GitHub](https://img.shields.io/github/license/Capsize-Games/airunner)
![GitHub last commit](https://img.shields.io/github/last-commit/Capsize-Games/airunner)
![GitHub issues](https://img.shields.io/github/issues/Capsize-Games/airunner)
![GitHub closed issues](https://img.shields.io/github/issues-closed/Capsize-Games/airunner)
![GitHub pull requests](https://img.shields.io/github/issues-pr/Capsize-Games/airunner)
![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed/Capsize-Games/airunner)

---

### Stable Diffusion on your own hardware 

No web server to run, additional requirements to install or technical knowledge required. 

[Just download the compiled package](https://capsizegames.itch.io/ai-runner) and start generating AI Art!

![Screenshot from 2023-06-30 10-43-49](https://github.com/Capsize-Games/airunner/assets/25737761/72e0dd26-53ca-4d5c-8f07-b6327a59b50c)

---

## ⭐ Features

AI Runner is a multi-modal AI application which allows you to run open-source 
large language models and AI image generators on your own hardware.

| Feature                                                             | Included |
|---------------------------------------------------------------------|:--------:|
| Have conversations with a chatbot using your voice                  |    ✅    |
| Text-to-speech                                                      |    ✅    |
| Speech-to-text                                                      |    ✅    |
| Vision-to-text                                                      |    ✅    |
| Text generation with large language models (LLMs)                   |    ✅    |
| Image generation using Stable Diffusion and Kandinsky               |    ✅    |
| Draw and generate images in near real-time                          |    ✅    |
| Run multiple models at once                                         |    ✅    |
| Easy setup - download and run. No need to install any requirements* | ✅ |
| Run offline, locally on your own hardware!                          |    ✅    |
| Fast! Generate images in approximately 2 seconds using an RTX 2080s | ✅ |
| text-to-image                                                       |    ✅    |
| image-to-image                                                      |    ✅    |
| inpaint and outpaint                                                |    ✅    |
| pix2pix                                                             |    ✅    |
| depth2img                                                           |    ✅    |
| controlnet                                                          |    ✅    |
| LoRA                                                                |    ✅    |
| textual embeddings                                                  |    ✅    |
| Drawing tools                                                       |    ✅    |
| Image filters                                                       |    ✅    |
| Dark mode                                                           |    ✅    |
| Infinite scrolling canvas                                           |    ✅    |
| NSFW filter toggle                                                  |    ✅    |
| NSFW guardrails to prevent harmful content                          |    ✅    |
| Standard Stable Diffusion settings                                  |    ✅    |
| Fast load time, responsive interface                                |    ✅    |
| Pure python - does not rely on a webserver                          |    ✅    |

---

## 💻 System Requirements

#### Minimum system requirements

- Cuda capable GPU
- 6gb of RAM
- 6gb of disc space to install AI Runner

#### Recommended system specs

- RTX 2080s or higher
- 32gb of RAM
- 100gb disc space

---

## 🔧 Installation

### Linux prerequisites

For emoji support on Ubuntu install the Noto Color Emoji font:

```bash
sudo apt install fonts-noto-color-emoji
```

Install `portaudio` and `libxcb-cursor`

```bash
sudo apt-get install libportaudio2 libxcb-cursor0
```

### PyPi

If you are on Windows, first install the following dependencies:
```bash
pip install pypiwin32
```

```bash
pip install airunner
```

### Source

If you want to install AI Runner from source, you can do so using the following command:

```bash
git clone -b develop https://github.com/Capsize-Games/airunner.git
cd airunner && pip install -e .
```

----

If you install from pypi or source, uninstall `opencv-python` (we use `opencv-python-headless` instead)

```bash
pip uninstall opencv-python
```

---

## 💿 Running AI Runner

There are many ways to run AI Runner, depending on your operating system and how you installed it.

### Pre-compiled

Unzip the AI Runner zip file which you downloaded from itch.io

#### Linux

```bash
cd airunner
./airunner
```

#### Windows

```bash
cd airunner
airunner.exe
```

Alternatively, you can use the itch.io launcher application which simplifies the process of downloading and running AI Runner.

---

### Compiled from source

```bash
cd dist/airunner
./airunner
```

---

### PyPi

```bash
python3 -m airunner
```

---

### Uncompiled Source

```bash
cd src/airunner
python main.py
```

---

### Docker

Linux:

```bash
docker-compose up linux
```

Windows:

```bash
docker-compose up windows
```

[See the installation 
wiki page for more information](https://github.com/Capsize-Games/airunner/wiki/Installation-instructions)

---

## ✏️ Using AI Runner

[Instructions on how to use AI Runner can be found in the wiki](https://github.com/Capsize-Games/airunner/wiki/AI-Runner)


---

## 💾 Compiling AI Runner

Clone this repository

```bash
git clone https://github.com/Capsize-Games/airunner.git
cd airunner
```

### Build from source

```bash
pip install -e .
pip install pyinstaller
bash build.dev.sh
```

### Build with Docker

#### Production

```bash
docker-compose run build
```

#### Develop

```bash
docker-compose run devbuild
```

---

## 🔬 Unit tests

Run a specific test
```bash
python -m unittest src/airunner/tests/test_draggable_pixmap.py
```

Test coverage is currently low, but the existing tests can be run using the following command:

```bash
python -m unittest discover tests
```

### Test coverage

Run tests with coverage tracking:

```bash
coverage run --source=src/airunner --omit=__init__.py,*/GFPGAN/*,*/data/*,*/tests/*,*_ui.py,*/enums.py,*/settings.py -m unittest discover src/airunner/tests
```

To see a report in the terminal, use:

```bash
coverage report
```

For a more detailed HTML report, run:

```bash
coverage html
```

View results in `htmlcov/index.html`.