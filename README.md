```
╔═════════════════════════════════════════════════════════════════════════════╗
║                                                                             ║
║     █████╗ ██╗    ██████╗ ██╗   ██╗███╗   ██╗███╗   ██╗███████╗██████╗      ║
║    ██╔══██╗██║    ██╔══██╗██║   ██║████╗  ██║████╗  ██║██╔════╝██╔══██╗     ║
║    ███████║██║    ██████╔╝██║   ██║██╔██╗ ██║██╔██╗ ██║█████╗  ██████╔╝     ║
║    ██╔══██║██║    ██╔══██╗██║   ██║██║╚██╗██║██║╚██╗██║██╔══╝  ██╔══██╗     ║
║    ██║  ██║██║    ██║  ██║╚██████╔╝██║ ╚████║██║ ╚████║███████╗██║  ██║     ║
║    ╚═╝  ╚═╝╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝     ║
║                                                                             ║
║                      Local AI Models Made Easy                              ║
║                                                                             ║
╚═════════════════════════════════════════════════════════════════════════════╝
Send Crypto: 0x02030569e866e22C9991f55Db0445eeAd2d646c8

AI Runner is an all-in-one, offline-first desktop application, headless server, and Python library for local LLMs, TTS, STT, and image generation.
```

[![Discord](https://img.shields.io/discord/839511291466219541?color=5865F2&logo=discord&logoColor=white)](https://discord.gg/ukcgjEpc5f) ![GitHub](https://img.shields.io/github/license/Capsize-Games/airunner) [![PyPi](https://github.com/Capsize-Games/airunner/actions/workflows/pypi-dispatch.yml/badge.svg)](https://github.com/Capsize-Games/airunner/actions/workflows/pypi-dispatch.yml) ![GitHub last commit](https://img.shields.io/github/last-commit/Capsize-Games/airunner)

[🐞 Report Bug](https://github.com/Capsize-Games/airunner/issues/new?template=bug_report.md) · [✨ Request Feature](https://github.com/Capsize-Games/airunner/issues/new?template=feature_request.md) · [🛡️ Report Vulnerability](https://github.com/Capsize-Games/airunner/issues/new?template=vulnerability_report.md) · [📖 Wiki](https://github.com/Capsize-Games/airunner/wiki)

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **🗣️ Voice Chat** | Real-time conversations with LLMs using espeak, SpeechT5, or OpenVoice TTS |
| **🤖 Custom AI Agents** | Configurable personalities, moods, and RAG-enhanced knowledge |
| **🎨 Visual Workflows** | Drag-and-drop LangGraph workflow builder with runtime execution |
| **🖼️ Image Generation** | Stable Diffusion (SD 1.5, SDXL) and FLUX models with drawing tools, LoRA, inpainting, and filters |
| **🔒 Privacy First** | Runs locally with no external APIs by default, configurable guardrails |
| **⚡ Fast Generation** | ~2s inference on RTX 2080s with GPU acceleration |

### 🌍 Language Support

| Language | TTS | LLM | STT | GUI |
|----------|-----|-----|-----|-----|
| English | ✅ | ✅ | ✅ | ✅ |
| Japanese | ✅ | ✅ | ❌ | ✅ |
| Spanish/French/Chinese/Korean | ✅ | ✅ | ❌ | ❌ |

[🫰 Request language support](https://github.com/Capsize-Games/airunner/issues/new?template=language_support.md)

---

## ⚙️ System Requirements

| | Minimum | Recommended |
|---|---------|-------------|
| **OS** | Ubuntu 22.04, Windows 10 | Ubuntu 22.04 (Wayland) |
| **CPU** | Ryzen 2700K / i7-8700K | Ryzen 5800X / i7-11700K |
| **RAM** | 16 GB | 32 GB |
| **GPU** | NVIDIA RTX 3060 | NVIDIA RTX 4090 |
| **Storage** | 22 GB (with models) | 100 GB+ |

---

## 💾 Installation

### Docker (Recommended)

**GUI Mode:**
```bash
xhost +local:docker && docker compose run --rm airunner
```

**Headless API Server:**
```bash
docker compose run --rm --service-ports airunner --headless
```

> **Note:** `--service-ports` is required to expose port 8080 for the API.

The headless server exposes an HTTP API on port 8080 with endpoints:
- `GET /health` - Health check and service status
- `POST /llm` - LLM inference
- `POST /art` - Image generation

### Manual Installation (Ubuntu/Debian)

**Python 3.13+ required.** We recommend using `pyenv` and `venv`.

1. **Install system dependencies:**
   ```bash
   sudo apt update && sudo apt install -y \
     build-essential cmake git curl wget \
     nvidia-cuda-toolkit pipewire libportaudio2 libxcb-cursor0 \
     espeak espeak-ng-espeak qt6-qpa-plugins qt6-wayland \
     mecab libmecab-dev mecab-ipadic-utf8 libxslt-dev mkcert
   ```

2. **Create data directory:**
   ```bash
   mkdir -p ~/.local/share/airunner
   ```

3. **Install AI Runner:**
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
   pip install airunner[all_dev]
   ```

4. **Run:**
   ```bash
   airunner
   ```

For detailed instructions, see the [Installation Wiki](https://github.com/Capsize-Games/airunner/wiki/Installation-instructions).

---

## 🤖 Models

AI Runner downloads essential TTS/STT models automatically. LLM and image models must be configured:

| Category | Model | Size |
|----------|-------|------|
| **LLM (default)** | Llama 3.1 8B Instruct (4bit) | ~4 GB |
| **Image** | Stable Diffusion 1.5 | ~2 GB |
| **Image** | SDXL 1.0 | ~6 GB |
| **Image** | FLUX.1 Dev/Schnell (GGUF) | 8-12 GB |
| **TTS** | OpenVoice / SpeechT5 | 654 MB - 4 GB |
| **STT** | Whisper Tiny | 155 MB |

**LLM Providers:** Local (HuggingFace), Ollama, OpenRouter, OpenAI

**Art Models:** Place your models in `~/.local/share/airunner/art/models/`

---

## 🛠️ CLI Commands

| Command | Description |
|---------|-------------|
| `airunner` | Launch GUI |
| `airunner-setup` | Download models |
| `airunner-build-ui` | Rebuild UI from `.ui` files |
| `airunner-tests` | Run test suite |
| `airunner-generate-cert` | Generate SSL certificate |

---

## 🔒 HTTPS Configuration

AI Runner's local server uses HTTPS by default. Certificates are auto-generated in `~/.local/share/airunner/certs/`.

For browser-trusted certificates, install [mkcert](https://github.com/FiloSottile/mkcert):
```bash
sudo apt install libnss3-tools
mkcert -install
```

---

## ⚖️ Colorado AI Act Notice

**Effective February 1, 2026**, the [Colorado AI Act (SB 24-205)](https://leg.colorado.gov/bills/sb24-205) regulates high-risk AI systems.

**Your Responsibility:** If you use AI Runner for decisions with legal or significant effects on individuals (employment screening, loan eligibility, insurance, housing), you may be classified as a **deployer of a high-risk AI system** and must:
- Implement a risk management policy
- Complete impact assessments
- Provide consumer notice and appeal mechanisms
- Report algorithmic discrimination to the Colorado Attorney General

**AI Runner's Design:** Local-first operation, configurable guardrails, and no external data transmission by default help support compliant use.

---

## 🧪 Testing

```bash
# Run headless-safe tests
pytest src/airunner/utils/tests/

# Run display-required tests (Qt/GUI)
xvfb-run -a pytest src/airunner/utils/tests/xvfb_required/
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [Development Wiki](https://github.com/Capsize-Games/airunner/wiki/Development).

## Documentation

- [Wiki](https://github.com/Capsize-Games/airunner/wiki)
- [API Service Layer](src/airunner/components/application/api/README.md)
- [ORM Models](src/airunner/components/data/models/README.md)