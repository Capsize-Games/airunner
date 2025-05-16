[![AI Runner Logo](images/banner.png)](https://github.com/Capsize-Games/airunner)

[![Discord](https://img.shields.io/discord/839511291466219541?color=5865F2&logo=discord&logoColor=white)](https://discord.gg/PUVDDCJ7gz)
![GitHub](https://img.shields.io/github/license/Capsize-Games/airunner)
[![PyPi](https://github.com/Capsize-Games/airunner/actions/workflows/pypi-dispatch.yml/badge.svg)](https://github.com/Capsize-Games/airunner/actions/workflows/pypi-dispatch.yml)
![GitHub last commit](https://img.shields.io/github/last-commit/Capsize-Games/airunner)

---

# Local Inference Made Easy

AI Runner is a local-first, open-source application that allows you to run large language models (LLMs) and image generation tools on your own hardware. It provides a user-friendly interface for creating chatbots, generating images, and performing various AI tasks without relying on external APIs.

![image](https://github.com/user-attachments/assets/392375c8-a7f6-4e6e-8662-511cffc608aa)

## System Requirements

| Specification       | Minimum                              | Recommended                          |
|---------------------|--------------------------------------------|--------------------------------------------|
| **OS**             | Ubuntu 22.04, Windows 10                               | Ubuntu 22.04 (Wayland)                              |
| **CPU**            | Ryzen 2700K or Intel Core i7-8700K         | Ryzen 5800X or Intel Core i7-11700K        |
| **Memory**         | 16 GB RAM                                  | 32 GB RAM                                  |
| **GPU**            | NVIDIA RTX 3060 or better                  | NVIDIA RTX 4090 or better                  |
| **Network**        | Broadband (used to download models)        | Broadband (used to download models)        |
| **Storage**        | 22 GB                                      | 50 GB                                      |
---

## 💾 Installation Quick Start

### Installation Steps

1. **Install system requirements**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3-openssl git nvidia-cuda-toolkit pipewire libportaudio2 libxcb-cursor0 gnupg gpg-agent pinentry-curses espeak xclip cmake qt6-qpa-plugins qt6-wayland qt6-gtk-platformtheme espeak espeak-ng-espeak mecab libmecab-dev mecab-ipadic-utf8
   ```
2. **Create `airunner` directory**
   ```bash
   sudo mkdir ~/.local/share/airunner
   sudo chown $USER:USER ~/.local/share/airunner
   ```
3. **Install AI Runner**
   ```bash
   pip install "typing-extensions==4.13.2"
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
   pip install airunner[all_dev]
   pip install -U timm
   ```
4. **Run AI Runner**
   ```bash
   airunner
   ```

For more options, including Docker, see the [Installation Wiki](https://github.com/Capsize-Games/airunner/wiki/Installation-instructions).

---

## Overview

![image](https://github.com/user-attachments/assets/b523c9e3-6a9b-4dfb-b66f-672b9b728f6e)

AI Runner is a local-first, **open-source** application built with HuggingFace and Llama-index libraries that enables you to run:

- ✅ **Large Language Models (LLMs)** for chat and text generation  
- ✅ **Stable Diffusion** for image generation and manipulation
- ✅ **Text-to-Speech (TTS)** Integrated with **OpenVoice**, **SpeechT5**, and **Espeak** for voice synthesis
- ✅ **Speech-to-Text (STT)** Uses **Whisper** for converting audio to text
- ✅ **Customizable Voice-based chatbots** for real-time conversations
- ✅ **Image filters** and **inpainting** for image editing
- ✅ **Retrieval-Augmented Generation** (RAG) for enhanced LLM responses
- ✅ **Wayland support, Python 3.13, Docker support, and a pure Python codebase** for improved security, performance, and compatibility

![interface/img.png](images/interface.png)

---

## Features

Below is a high-level list of capabilities in AI Runner:

| Feature                                  | Description                                                                                  |
|------------------------------------------|----------------------------------------------------------------------------------------------|
| **LLMs & Communication**                 |                                                                                              |
| Voice-based chatbot conversations        | Have real-time voice-chat sessions with an LLM (speech-to-text + text-to-speech)            |
| Text-to-speech (TTS)                     | Convert text to spoken audio using **OpenVoice**, **SpeechT5**, and **Espeak**                                       |
| Speech-to-text (STT)                     | Convert spoken audio to text with **Whisper**                                                   |
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
| OpenVoice (Voice)       | ... |

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
Get started with local AI inference in minutes—no more endless environment setup.  
Questions or ideas? Join our [Discord](https://discord.gg/PUVDDCJ7gz) or open a [GitHub Issue](https://github.com/Capsize-Games/airunner/issues).  

**Happy building!**
