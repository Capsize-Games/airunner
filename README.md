[![AI Runner Logo](images/banner.png)](https://github.com/Capsize-Games/airunner)


# Offline AI interface for Hackers, Makers, and Builders [![Discord](https://img.shields.io/discord/839511291466219541?color=5865F2&logo=discord&logoColor=white)](https://discord.gg/PUVDDCJ7gz) ![GitHub](https://img.shields.io/github/license/Capsize-Games/airunner) [![PyPi](https://github.com/Capsize-Games/airunner/actions/workflows/pypi-dispatch.yml/badge.svg)](https://github.com/Capsize-Games/airunner/actions/workflows/pypi-dispatch.yml) ![GitHub last commit](https://img.shields.io/github/last-commit/Capsize-Games/airunner)

<table>
  <tr>
    <td valign="top">

<div style="border: 2px solid blue; border-radius: 8px; margin-bottom: 10px; padding: 16px; background-color: #f9f9f9; box-shadow: 0 2px 8px #0002; background: transparent; max-width: 250px">

| ✨ Key Features |
|:--------------------------------|
| **🗣️ Real-time conversations** |
| - Three speech engines: espeak, SpeechT5, OpenVoice<br>- Auto language detection (OpenVoice)<br>- Real-time voice-chat with LLMs |
| **🤖 Customizable AI Agents** |
| - Custom agent names, moods, personalities<br>- Retrieval-Augmented Generation (RAG)<br>- Create AI personalities and moods |
| **📚 Enhanced Knowledge Retrieval** |
| - RAG for documents/websites<br>- Use local data to enrich chat |
| **🖼️ Image Generation & Manipulation** |
| - Text-to-Image (Stable Diffusion 1.5, SDXL, Turbo)<br>- Drawing tools & ControlNet<br>- LoRA & Embeddings<br>- Inpainting, outpainting, filters |
| **🌍 Multi-lingual Capabilities** |
| - Partial multi-lingual TTS/STT/interface<br>- English & Japanese GUI |
| **🔒 Privacy and Security** |
| - Runs locally, no external API (default)<br>- Customizable LLM guardrails & image safety<br>- Disables HuggingFace telemetry<br> - Restricts network access |
| **⚡ Performance & Utility** |
| - Fast generation (~2s on RTX 2080s)<br>- Docker-based setup & GPU acceleration<br>- Theming (Light/Dark/System)<br>- NSFW toggles<br>- Extension API<br>- Python library & API support |

</div>
<div style="border: 2px solid pink; border-radius: 8px; margin-bottom: 10px; padding: 16px; background-color: #f9f9f9; box-shadow: 0 2px 8px #0002; background: transparent;">

</div>
<div style="border: 2px solid green; border-radius: 8px; margin-bottom: 10px; padding: 16px; background-color: #f9f9f9; box-shadow: 0 2px 8px #0002; background: transparent;">

### 🌍 Language Support

| Language         | TTS | LLM | STT | GUI |
|------------------|-------------|-------------|-------------|-------------|
| English          | ✅          | ✅          | ✅          | ✅          |
| Japanese         | ✅          | ✅          | ❌          | ✅          |
| Spanish          | ✅          | ✅          | ❌          | ❌          |
| French           | ✅          | ✅          | ❌          | ❌          |
| Chinese          | ✅          | ✅          | ❌          | ❌          |
| Korean           | ✅          | ✅          | ❌          | ❌          |

[Request language support](https://github.com/Capsize-Games/airunner/issues/new/choose)

</div>
</td>
<td valign="top">

<img src="https://github.com/user-attachments/assets/392375c8-a7f6-4e6e-8662-511cffc608aa" alt="AI Runner Screenshot" style="max-width: 100%; border-radius: 8px; box-shadow: 0 2px 8px #0002;">

<video src="https://github.com/user-attachments/assets/2d5b41ff-a0cd-4239-945b-d9e7a1bc5644" controls width="100%" style="border-radius: 8px; box-shadow: 0 2px 8px #0002;"></video>

</td>
</tr>
</table>

---

## ⚙️ System Requirements

| Specification       | Minimum                              | Recommended                          |
|---------------------|--------------------------------------------|--------------------------------------------|
| **OS** | Ubuntu 22.04, Windows 10                   | Ubuntu 22.04 (Wayland)                     |
| **CPU** | Ryzen 2700K or Intel Core i7-8700K         | Ryzen 5800X or Intel Core i7-11700K        |
| **Memory** | 16 GB RAM                                  | 32 GB RAM                                  |
| **GPU** | NVIDIA RTX 3060 or better                  | NVIDIA RTX 4090 or better                  |
| **Network** | Broadband (used to download models)        | Broadband (used to download models)        |
| **Storage** | 22 GB (with models), 6 GB (without models) | 100 GB or higher                           |

## 💾 Installation Quick Start

### 🔧 Installation Steps

There are several ways to install and use AI Runner. [See the Installation Wiki for the full instructions](https://github.com/Capsize-Games/airunner/wiki/Installation-instructions). The following steps are for a developer quick start on **Ubuntu 22.04** (these instructions should also work on 24.04 and any LTS version of Ubuntu). The wiki has instructions for the compiled version (currently unavailable), Windows, and Docker.

1. **Install system requirements**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3-openssl git nvidia-cuda-toolkit pipewire libportaudio2 libxcb-cursor0 gnupg gpg-agent pinentry-curses espeak xclip cmake qt6-qpa-plugins qt6-wayland qt6-gtk-platformtheme mecab libmecab-dev mecab-ipadic-utf8 libxslt-dev
   sudo apt install espeak
   sudo apt install espeak-ng-espeak
   ```
2. **Create `airunner` directory**
   ```bash
   sudo mkdir ~/.local/share/airunner
   sudo chown $USER:$USER ~/.local/share/airunner
   ```
3. **Install AI Runner** - **Python 3.13+ required** `pyenv` and `venv` are recommended ([see wiki](https://github.com/Capsize-Games/airunner/wiki/Installation-instructions) for more info)
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

**Note: *AI Runner does not distribute AI art models. You are responsible for obtaining and your own.***

---

## 🛠️ Usage

### Basic Usage

- **Run AI Runner**: `airunner`
- **Build templates**: `airunner-build-ui`

---

## ✨ LLM Vendors

- **Default local model:** Ministral 8b instruct 4bit
- **Ollama:**: A variety of local models to choose from (requires Ollama CLI)
- **OpenRouter**: Remove server-side LLMs (requires API key)
- **Huggingface**: Coming soon

---

## 🤖 Models

These are the sizes of the various models that power AI Runner.

| Modality         | Model | Size |
|------------------|-------|------|
| **Text-to-Speech** | OpenVoice (Voice) | 4.0 GB |
| | Speech T5 (Voice) | 654.4 MB |
| | Whisper Tiny | 155.4 MB |
| **Speech-to-Text** | Whisper Tiny | 155.4 MB |
| **Text Generation** | Ministral 8b (default) | 4.0 GB |
| | Ollama (various models) | 1.5 GB - 20 GB |
| | OpenRouter (various models) | 1.5 GB - 20 GB |
| | Huggingface (various models) | 1.5 GB - 20 GB |
| | Local (Ministral instruct 8b 4bit doublequantized) | 5.8bit |
| **Image Generation** | Controlnet (SD 1.5) | 10.6 GB |
| | Controlnet (SDXL) | 320.2 MB |
| | Safety Checker + Feature Extractor | 3.2 GB |
| | SD 1.5 | 1.6 MB |
| | SDXL 1.0 | 6.45 MB |

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
- **Wayland support**, **Python 3.13**, and the latest stable torch libraries for extra security, performance, and compatibility.

---

## Contributing

We welcome pull requests for new features, bug fixes, or documentation improvements. You can also build and share **extensions** to expand AI Runner’s functionality. For details, see the [Extensions Wiki](https://github.com/Capsize-Games/airunner/wiki/Extensions).

Take a look at the [Contributing document](https://github.com/Capsize-Games/airunner/CONTRIBUTING.md) and the [Development wiki page](https://github.com/Capsize-Games/airunner/wiki/Development) for detailed instructions.

---

## Thank You!

Thanks for checking out AI Runner.
Questions or ideas? Join our [Discord](https://discord.gg/PUVDDCJ7gz) or open a [GitHub Issue](https://github.com/Capsize-Games/airunner/issues).
