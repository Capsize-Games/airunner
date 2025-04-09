[![AI Runner Logo](images/banner.png)](https://github.com/Capsize-Games/airunner)

[![Discord](https://img.shields.io/discord/839511291466219541?color=5865F2&logo=discord&logoColor=white)](https://discord.gg/PUVDDCJ7gz)
[![PyPi](https://github.com/Capsize-Games/airunner/actions/workflows/pypi-dispatch.yml/badge.svg)](https://github.com/Capsize-Games/airunner/actions/workflows/pypi-dispatch.yml)
![GitHub](https://img.shields.io/github/license/Capsize-Games/airunner)
![GitHub last commit](https://img.shields.io/github/last-commit/Capsize-Games/airunner)
![GitHub issues](https://img.shields.io/github/issues/Capsize-Games/airunner)
![GitHub closed issues](https://img.shields.io/github/issues-closed/Capsize-Games/airunner)
![GitHub pull requests](https://img.shields.io/github/issues-pr/Capsize-Games/airunner)
![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed/Capsize-Games/airunner)

---

# AI Runner 

**Run local AI models for text, images, text-to-speech, and speech-to-text—all in one open-source tool.**  
No cloud dependency. No complicated setup. Just install, run, and create.

![image](https://github.com/user-attachments/assets/392375c8-a7f6-4e6e-8662-511cffc608aa)

## Table of Contents
- [Overview](#overview)
- [Why Developers Use AI Runner](#why-developers-use-ai-runner)
- [Features](#features)
- [System Requirements](#system-requirements)
- [Quick Start (Docker)](#quick-start-docker)
- [Installation Details](#installation-details)
- [AI Models](#ai-models)
- [Unit Tests](#unit-tests)
- [Database](#database)
- [Advanced Features](#advanced-features)
- [Missing or Planned Features](#missing-or-planned-features)
- [Contributing](#contributing)

---

## Overview

AI Runner is a local-first, **open-source** application that enables you to run:

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

## Why Developers Use AI Runner

![images/img.png](images/img.png)

1. **Fast Setup with Docker**  
   No need to configure Python environments manually—just pull and run. AI Runner includes all major dependencies, plus GPU support (with [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)).

2. **Local LLM & Stable Diffusion in One**  
   Stop juggling separate repos for text generation and image generation. AI Runner unifies them under one interface.

3. **Plugin & Extension System**  
   Extend or modify AI Runner’s GUI or back-end with custom plugins. Add new model workflows, custom UI panels, or special logic without forking the entire codebase.

4. **Python Library**  
   Install from PyPi and **import** AI Runner directly into your Python project (e.g., a game in Pygame or a PySide6 desktop app).

5. **Offline / Private Data**  
   Keep data on-premise or behind a firewall—great for enterprise or regulated environments that can’t rely on external cloud inference.

If you find it helpful, please **star this repo** and share it with others—it helps the project grow and signals demand for local AI solutions.

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

### Minimum Specs

- **OS**: Linux or Windows  
- **CPU**: Intel i5 (or equivalent)  
- **Memory**: 16 GB RAM  
- **GPU**: NVIDIA RTX 3060 or better (for Stable Diffusion, TTS/Whisper)  
- **Network**: Broadband (used to download models)  
- **Storage**: 130 GB free (model files can be large)

### Recommended Specs

- **OS**: Ubuntu 22.04  
- **CPU**: Intel i7 (or equivalent)  
- **Memory**: 30+ GB RAM  
- **GPU**: NVIDIA RTX 4090 or higher  
- **Storage**: 130 GB free  
- **Network**: Needed initially for model downloads

---

## Quick Start (Docker)

**Recommended for most developers**—it avoids Python environment headaches and streamlines GPU access.

1. **Install NVIDIA Container Toolkit**  
   Follow the [official guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) to enable GPU passthrough for Docker.

2. **Get the latest docker image**
   ```bash
   docker pull ghcr.io/capsize-games/airunner/airunner:dev_latest
   ```

3. **Clone AI Runner and Run Setup**  
   ```bash
   git clone https://github.com/Capsize-Games/airunner.git
   cd airunner
   python3 -m venv venv
   source venv/bin/activate
   ./src/airunner/bin/setup.sh
   ```
   - _Choose option **1** (Setup xhost)_
   - _Choose option **2** (Install AI Runner scripts)_

5. **Start AI Runner**
   ```bash
   airunner-docker airunner
   ```
   This starts the GUI with stable diffusion, LLM, TTS/STT, and more.

For detailed steps, see the [Installation Wiki](https://github.com/Capsize-Games/airunner/wiki/Installation-instructions).

---

## Installation Details

If you prefer **not** to use Docker, see the [Installation Wiki for more information](https://github.com/Capsize-Games/airunner/wiki/Installation-instructions).

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

## Missing or Planned Features

- Additional model auto-downloaders  
- Automated plugin discovery from community repositories  
- Fine-tuning workflow for LLMs  
- Desktop packaging (PyInstaller or similar)

---

## Contributing

We welcome pull requests for new features, bug fixes, or documentation improvements. You can also build and share **extensions** to expand AI Runner’s functionality. For details, see the [Extensions Wiki](https://github.com/Capsize-Games/airunner/wiki/Extensions).

**If you find this project useful**, please consider giving us a ⭐ on GitHub—it really helps with visibility and encourages further development.

---

## Thank You!

Thanks for checking out AI Runner.  
**Get started** with local AI inference in minutes—no more endless environment setup.  
Questions or ideas? Join our [Discord](https://discord.gg/PUVDDCJ7gz) or open a [GitHub Issue](https://github.com/Capsize-Games/airunner/issues).  

**Happy building!**
