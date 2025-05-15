[![AI Runner Logo](images/banner.png)](https://github.com/Capsize-Games/airunner)

[![Discord](https://img.shields.io/discord/839511291466219541?color=5865F2&logo=discord&logoColor=white)](https://discord.gg/PUVDDCJ7gz)
![GitHub](https://img.shields.io/github/license/Capsize-Games/airunner)
[![PyPi](https://github.com/Capsize-Games/airunner/actions/workflows/pypi-dispatch.yml/badge.svg)](https://github.com/Capsize-Games/airunner/actions/workflows/pypi-dispatch.yml)
![GitHub last commit](https://img.shields.io/github/last-commit/Capsize-Games/airunner)

---

# AI Runner 

**Run local AI models for text, images, text-to-speech, and speech-to-text—all in one open-source tool.**  
No cloud dependency. No complicated setup. Just install, run, and create.

![image](https://github.com/user-attachments/assets/392375c8-a7f6-4e6e-8662-511cffc608aa)
<small>**Art tools**</small>

![image](https://github.com/user-attachments/assets/b523c9e3-6a9b-4dfb-b66f-672b9b728f6e)
<small>**Agent workflows**</small>

---

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation Quick Start](#installation-quick-start-development-version)
- [Installation Details](#installation-details)
- [AI Models](#ai-models)
- [Unit Tests](#unit-tests)
- [Database](#database)
- [Advanced Features](#advanced-features)
- [Contributing](#contributing)

---

## Overview

AI Runner is a local-first, **open-source** application built with HuggingFace and Llama-index libraries that enables you to run:

- **Large Language Models (LLMs)** for chat and text generation  
- **Stable Diffusion** for image generation and manipulation
- **Text-to-Speech (TTS)**  
- **Speech-to-Text (STT)**  

Originally created as a GUI-centric AI art and chatbot tool for end users, AI Runner has evolved into a **developer-friendly** platform. With Docker support, an extension API, and a pure Python codebase, you can integrate AI Runner into your own apps or use it as an all-in-one offline inference engine.

![interface/img.png](images/interface.png)

**Typical Uses:**
- AI prototyping: Quickly test local LLMs and image generation.  
- Offline scenarios: Work behind firewalls or without internet.  
- Custom UI/UX: Build plugins/extensions for your particular domain.  
- End-user tools: Hand off a no-code (GUI) solution for less technical stakeholders.

---

## Features

Below is a high-level list of capabilities in AI Runner:

| Feature                                  | Description                                                                                  |
|------------------------------------------|----------------------------------------------------------------------------------------------|
| **LLMs & Communication**                 |                                                                                              |
| Voice-based chatbot conversations        | Have real-time voice-chat sessions with an LLM (speech-to-text + text-to-speech)            |
| Text-to-speech (TTS)                     | Convert text to spoken audio using Espeak or SpeechT5                                       |
| Speech-to-text (STT)                     | Convert spoken audio to text with Whisper                                                   |
| Customizable chatbots                    | Create AI personalities and moods for more engaging conversations                            |
| Retrieval-Augmented Generation           | Use local doc or website data to enrich chat responses                                      |
| **Image Generation**                     |                                                                                              |
| Stable Diffusion (1.5, SDXL, Turbo)      | Generate images from textual prompts, sketches, or existing images                           |
| Drawing tools & ControlNet              | Fine-tune image outputs with extra input or guides                                          |
| LoRA & Embeddings                        | Load LoRA models or textual embeddings for specialized image generation                     |
| **Image Manipulation**                   |                                                                                              |
| Inpaint & Outpaint                       | Modify portions of generated images while keeping context                                   |
| Image filters                            | Blur, film grain, pixel art, etc.                                                            |
| **Utility**                              |                                                                                              |
| **Offline**                              | Everything runs locally, no external API required                                           |
| Fast generation                          | E.g., ~2 seconds on an RTX 2080s for stable diffusion                                        |
| Docker-based approach                    | Simplifies setup & ensures GPU acceleration works out of the box                            |
| Dark mode                                | Built-in theming (Light / Dark / System)                                                    |
| NSFW toggles                             | Enable or disable NSFW detection for images                                                 |
| Ethical guardrails                       | Basic guardrails for safe LLM usage (optional)                                              |
| **Extensions**                           | Build your own feature add-ons via the extension API                                        |
| **Python Library**                       | `pip install airunner` and embed it in your own projects                                    |
| **API Support**                          | Optionally use OpenRouter or other external LLMs                                            |

---

## System Requirements

### System Requirements

| Specification       | Minimum                              | Recommended                          |
|---------------------|--------------------------------------------|--------------------------------------------|
| **OS**             | Ubuntu 22.04, Windows 10                               | Ubuntu 22.04 (Wayland)                              |
| **CPU**            | Ryzen 2700K or Intel Core i7-8700K         | Ryzen 5800X or Intel Core i7-11700K        |
| **Memory**         | 16 GB RAM                                  | 32 GB RAM                                  |
| **GPU**            | NVIDIA RTX 3060 or better                  | NVIDIA RTX 4090 or better                  |
| **Network**        | Broadband (used to download models)        | Broadband (used to download models)        |
| **Storage**        | 22 GB                                      | 50 GB                                      |
---

### Models

These are the sizes of the various models that power AI Runner.

| Model                | Size     |
|-------------------------|----------|
| Controlnet (SD 1.5)             | 10.6 GB  |
| Controlnet (SDXL)             | 320.2 MB  |
| Safety Checker + Feature Extractor               | 3.2 GB   |
| SD 1.5                | 1.6 MB   |
| SDXL 1.0                | 6.45 MB   |
| LLM                     | 5.8 GB   |
| e5 large (embedding model) | 1.3 GB   |
| Whisper Tiny            | 155.4 MB |
| Speech T5 (Voice)       | 654.4 MB |

---

## 💾 Installation Quick Start (development version)

### 🐳 Docker

**Recommended for most developers**—it avoids Python environment headaches and streamlines GPU access.

**Note:** 

AI Runner's Docker setup uses Wayland by default for optimal performance and compatibility with modern Linux desktop environments. This means you will need wayland support on your host system.

1. **Install NVIDIA Container Toolkit**  
   Follow the [official guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) to enable GPU passthrough for Docker.
2. **Clone AI Runner**
   ```bash
   git clone https://github.com/Capsize-Games/airunner.git
   cd airunner
   ./src/airunner/bin/docker.sh airunner
   ```

#### Custom docker compose file

Docker compose allows you to customize the container environment.

For example, if you want access to a directory on your host machine, you can mount it in the container by creating a `airunner/package/dev/docker-compose.local.yml` file with the following content

```yaml
version: '3.8'

services:
  airunner_dev:
    volumes:
      - /mnt/YourDrive:/mnt/YourDrive:rw,z
```

---

### 🖥️ Ubuntu (including Windows WSL 2)

Choose this if you want to run AI Runner natively on your machine without Docker.

These instructions will assume the following directory structure. *You should only deviate from this structure if you know what you're doing.*

```plaintext
~/Projects
├── airunner
├── OpenVoice
└── venv
```

1. Install system requirements
   **All platforms**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3-openssl git nvidia-cuda-toolkit pipewire libportaudio2 libxcb-cursor0 gnupg gpg-agent pinentry-curses espeak xclip cmake qt6-qpa-plugins qt6-wayland qt6-gtk-platformtheme espeak-ng-espeak
   ```
   **Linux**
   ```bash
   sudo apt install -y espeak
   ```
   **Windows**
   ```bash
   sudo apt install -y espeak-ng-espeak
   ```
2. Create airunner directory
   ```bash
   sudo mkdir ~/.local/share/airunner
   sudo chown $USER:USER ~/.local/share/airunner
   ```
3. Install pyenv (allows management of multiple Python versions)
   ```bash
   curl https://pyenv.run | bash
   ```
4. Add pyenv to shell configuration
```bash
# Check and add pyenv configuration if not already present
if ! grep -q "Pyenv configuration added by AI Runner" ~/.bashrc; then
     cat << 'EOF' >> ~/.bashrc

# Pyenv configuration added by AI Runner setup
export PYENV_ROOT="$HOME/.pyenv"
if [ -d "$PYENV_ROOT/bin" ]; then
  export PATH="$PYENV_ROOT/bin:$PATH"
fi
if command -v pyenv &>/dev/null; then
  eval "$(pyenv init - bash)"
fi
EOF
   fi

   # Check and add WSLg XDG_RUNTIME_DIR fix if not already present
   if ! grep -q "WSLg XDG_RUNTIME_DIR Fix added by AI Runner" ~/.bashrc; then
     cat << 'EOF' >> ~/.bashrc

# WSLg XDG_RUNTIME_DIR Fix added by AI Runner setup
if [ -n "$WSL_DISTRO_NAME" ]; then
    if [ -d "/wslg/runtime-dir" ]; then
        export XDG_RUNTIME_DIR="/wslg/runtime-dir"
    elif [ -d "/mnt/wslg/runtime-dir" ]; then # Older WSLg path
        export XDG_RUNTIME_DIR="/mnt/wslg/runtime-dir"
    fi
fi
EOF
   fi

   # Check and add Qt environment variables for WSLg if not already present
   if ! grep -q "Qt environment variables for WSLg added by AI Runner" ~/.bashrc; then
     cat << 'EOF' >> ~/.bashrc

# Qt environment variables for WSLg added by AI Runner setup
if [ -n "$WSL_DISTRO_NAME" ]; then
    export QT_QPA_PLATFORM=wayland
    export QT_QPA_PLATFORMTHEME=gtk3
fi
EOF
fi
```
5. Install python and set to local version
   ```bash
   . ~/.bashrc
   pyenv install 3.13.3
   ```
6. Clone repo, set local python version, create virtual env, activate it
   ```bash
   mkdir ~/Projects
   cd ~/Projects
   pyenv local 3.13.3
   python -m venv venv
   source ./venv/bin/activate
   git clone https://github.com/Capsize-Games/airunner.git
   ```
7. Install AI Runner requirements
   ```bash
   pip install "typing-extensions==4.13.2"
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
   pip install -e airunner[all_dev]
   pip install -U timm
   python -c "import nltk; nltk.download('punkt')"
   python -c "import nltk; nltk.download('punkt_tab')"
   ```
8. Run app 
   ```bash
   airunner
   ```

**Optional**

- [OpenVoice](https://github.com/Capsize-Games/airunner/wiki/Modules#openvoice)
- Flash attention 2
- xformers
- FramePack

---

## AI Models

By default, AI Runner installs essential TTS/STT and minimal LLM components.  
You **must supply** additional Stable Diffusion models (e.g., from [Hugging Face](https://huggingface.co/) or [Civitai](https://civitai.com/)).

Organize them under your local AI Runner data directory:
```plaintext
~/.local/share/airunner
├── art
│   └── models
│       ├── SD 1.5
│       │   ├── lora
│       │   └── embeddings
│       ├── Flux
│       ├── SDXL 1.0
│       │   ├── lora
│       │   └── embeddings
│       └── SDXL Turbo
│           ├── lora
│           └── embeddings
```

---

## Unit Tests

To run all tests:

```bash
python -m unittest discover -s src/airunner/tests
```

Or a single test:

```bash
python -m unittest src/airunner/tests/test_prompt_weight_convert.py
```

---

## Database

AI Runner supports a simple database system. See the [Wiki](https://github.com/Capsize-Games/airunner/wiki/Database) for how to:
- Switch engines (SQLite, etc.)
- Make schema changes
- Run migrations

---

## Advanced Features

- **Memory Optimization**: TF32 Mode, VAE/Attention Slicing, Torch 2.0, sequential CPU offload, ToMe token merging.  
- **Experimental Integrations**: Weather-based chatbot prompts, advanced command-line arguments (`--perform-llm-analysis`, `--disable-setup-wizard`, etc.).  
- **Safety & Guardrails**: Optional NSFW content detection and adjustable guardrails for LLMs.  

---

## Contributing

We welcome pull requests for new features, bug fixes, or documentation improvements. You can also build and share **extensions** to expand AI Runner’s functionality. For details, see the [Extensions Wiki](https://github.com/Capsize-Games/airunner/wiki/Extensions).

Take a look at the [Contributing document](https://github.com/Capsize-Games/airunner/CONTRIBUTING.md) and the [Development wiki page](https://github.com/Capsize-Games/airunner/wiki/Development) for detailed instructions.

---

## Thank You!

Thanks for checking out AI Runner.  
**Get started** with local AI inference in minutes—no more endless environment setup.  
Questions or ideas? Join our [Discord](https://discord.gg/PUVDDCJ7gz) or open a [GitHub Issue](https://github.com/Capsize-Games/airunner/issues).  

**Happy building!**
