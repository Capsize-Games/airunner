# AI Runner

> Edge AI inference engine with a web GUI — LLMs, image generation, voice chat, and agents running entirely on your hardware, at the edge.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Stars](https://img.shields.io/github/stars/Capsize-Games/airunner?style=social)](https://github.com/Capsize-Games/airunner/stargazers)

[🐞 Report Bug](https://github.com/Capsize-Games/airunner/issues/new?template=bug_report.md) · [✨ Request Feature](https://github.com/Capsize-Games/airunner/issues/new?template=feature_request.md) · [🛡️ Report Vulnerability](https://github.com/Capsize-Games/airunner/issues/new?template=vulnerability_report.md) · [📖 Wiki](https://github.com/Capsize-Games/airunner/wiki)

---

## What is AI Runner?

AI Runner is a privacy-first edge AI platform — all inference runs locally on your own hardware, not in the cloud. It runs a Python backend that handles model inference and exposes a REST API, paired with a React web frontend you access in your browser. Your prompts, images, and voice data never leave your machine.

**Architecture at a glance:**

```
airunner_web_client/   ← React + Vite frontend (port 5173)
services/src/          ← Python inference backend (port 8080)
```

---

## ✨ Features

| Feature | Description |
|---|---|
| **🤖 LLM Chat** | Local LLMs via llama.cpp (GGUF), with optional OpenRouter/OpenAI backends |
| **🗣️ Voice Chat** | Real-time speech-to-text and text-to-speech for hands-free conversations |
| **🎨 Image Generation** | Stable Diffusion (SD 1.5, SDXL) and FLUX with LoRA and inpainting |
| **🧠 AI Agents** | Configurable personalities, moods, RAG-enhanced memory, and tool use |
| **🔒 Privacy First** | Runs fully offline by default — no data leaves your machine |
| **🌐 Web UI** | React frontend, accessible from any browser on your local network |
| **⚡ Optimized** | GGUF quantization, attention slicing, and VRAM offloading for lower-end hardware |

---

## ⚙️ System Requirements

| | Minimum | Recommended |
|---|---|---|
| **OS** | Ubuntu 22.04 | Ubuntu 24.04 |
| **CPU** | Ryzen 2700K / i7-8700K | Ryzen 5800X / i7-11700K |
| **RAM** | 16 GB | 32 GB |
| **GPU** | NVIDIA RTX 3060 | NVIDIA RTX 4080+ |
| **Storage** | 22 GB SSD | 100 GB+ SSD |
| **Python** | 3.13.3+ | 3.13.3+ |

---

## 🚀 Quick Start

### Install

Clone the repo and run the install script:

```bash
git clone https://github.com/Capsize-Games/airunner.git
cd airunner
./scripts/install.sh
```

This installs the Python backend and all frontend dependencies.

### Run

```bash
./scripts/run_web.sh
```

Then open your browser at **http://localhost:5173**.

The backend API is available at **http://localhost:8080**.

---

## 📦 End-User Bundle (Desktop Application)

For non-developer users, AI Runner provides a self-contained desktop application
via **Electron**.  The bundle includes an embedded Python runtime, all Python
dependencies, CUDA-accelerated `llama.cpp` and `whisper.cpp` binaries, and the
compiled React frontend — all in a single installable package.

**No Python, Node.js, CMake, C++ compiler, or CUDA toolkit is required.**
Only an NVIDIA GPU driver (525+) is needed.

### Platforms

| Platform | Installer Format | GPU |
|----------|-----------------|-----|
| Linux    | `.AppImage`, `.deb` | NVIDIA (CUDA, Ampere+) |
| Windows  | `.exe` (NSIS) | NVIDIA (CUDA, Ampere+) |

### Download

Pre-built installers are attached to each [GitHub Release](https://github.com/Capsize-Games/airunner/releases)
tagged with a `v*` version.  Look for artifacts named:

- `airunner-bundle-linux-*.AppImage` or `airunner-bundle-linux-*.deb`
- `airunner-bundle-win32-*.exe`

### How it works

```
Electron app
├── main process (Node.js)
│   ├── Spawns the embedded Python backend as a child process
│   ├── Polls GET /health until the backend is ready
│   ├── Loads the React frontend once the backend is healthy
│   └── Kills the backend on app quit
└── renderer process
    └── Loads http://localhost:8080 (served by the Python backend)

electron/resources/
├── python/     ← embedded CPython 3.13 + all pip dependencies + CUDA native libs
└── web/        ← compiled React frontend (airunner_web_client/dist/)
```

### Building from source (for maintainers)

```bash
# Linux
./package/build_bundle.sh

# Windows (PowerShell)
.\package\build_bundle.ps1
```

Prerequisites on the build host: CUDA toolkit 12.x, CMake ≥ 3.24,
Node.js ≥ 20, and a C++ compiler.  These are **not** required on the
end user's machine.

---

## 💾 Manual Installation (Advanced)

If you need fine-grained control, the install script supports three modes:

```bash
# Developer mode — installs from source (default for contributors)
./scripts/install.sh

# Distributed mode — for server/multi-machine deployments
./deployment/install_distributed.sh

# Single-package mode — installs a prebuilt self-contained bundle
./package/build_bundle.sh
```

### Python dependencies

**Python 3.13.3+ is required.** We recommend `pyenv` + `venv`.

Install PyTorch first:

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

Then install the backend package:

```bash
pip install -e "services/src/.[core,llm-native,stt-native,art-python,tts-python]"
```

### llama-cpp-python (CUDA build)

```bash
CMAKE_ARGS="-DGGML_CUDA=on -DGGML_CUDA_ARCHITECTURES=90" FORCE_CMAKE=1 \
  pip install --no-binary=:all: --no-cache-dir "llama-cpp-python==0.3.21"
```

> `90` targets RTX 4090/5080-class GPUs. Drop `-DGGML_CUDA_ARCHITECTURES` to auto-detect your GPU.

---


## 🤖 Models

Essential TTS/STT models download automatically on first run. LLM and image models must be configured manually.

| Category | Model | Size |
|---|---|---|
| **LLM (default)** | Ministral-8B-Instruct (GGUF) | ~4 GB |
| **Image** | Stable Diffusion 1.5 | ~2 GB |
| **Image** | SDXL 1.0 | ~6 GB |
| **Image** | FLUX.1 Dev/Schnell (GGUF) | 8–12 GB |
| **TTS** | OpenVoice | 654 MB |
| **STT** | Whisper Tiny | 155 MB |

Place art models in `~/.local/share/airunner/art/models/`.

---


## 🔒 HTTPS

The local server uses HTTPS by default. Certificates are auto-generated at `~/.local/share/airunner/certs/`.

For browser-trusted certificates, install [mkcert](https://github.com/FiloSottile/mkcert):

```bash
sudo apt install libnss3-tools
mkcert -install
airunner-generate-cert
```

---

## 🧪 Testing

```bash
# Run the full test suite
airunner-tests

# Run headless-safe tests directly
pytest services/src/

# With coverage
airunner-test-coverage-report
```

---

## ⚖️ Colorado AI Act Notice

**Effective February 1, 2026**, the [Colorado AI Act (SB 24-205)](https://leg.colorado.gov/bills/sb24-205) regulates high-risk AI systems. If you use AI Runner to make decisions with legal or significant effects on individuals (employment screening, loan eligibility, housing, etc.), you may be classified as a **deployer of a high-risk AI system** and subject to compliance obligations.

AI Runner is designed to run fully locally with no external data transmission by default. Optional features that do connect externally: model downloads (HuggingFace/CivitAI), web search (DuckDuckGo), weather prompts (Open-Meteo), and external LLM providers (OpenRouter/OpenAI) if configured. We recommend using a VPN when using these features.

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [Development Wiki](https://github.com/Capsize-Games/airunner/wiki/Development).

## 📚 Documentation

- [Wiki](https://github.com/Capsize-Games/airunner/wiki)
- [Settings Reference](https://github.com/Capsize-Games/airunner/wiki/Settings)
- [API Service Layer](src/airunner/components/application/api/README.md)

---

## License

MIT License — see [LICENSE](LICENSE) for details.

[![AI Runner](https://airunner.org/logo.png)](https://airunner.org)
