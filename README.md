[![AI Runner](images/banner.png)](https://github.com/Capsize-Games/airunner)


<img src="https://github.com/user-attachments/assets/392375c8-a7f6-4e6e-8662-511cffc608aa" alt="AI Runner Screenshot" style="max-width: 100%; border-radius: 8px; box-shadow: 0 2px 8px #0002;">

<video src="https://github.com/user-attachments/assets/2d5b41ff-a0cd-4239-945b-d9e7a1bc5644" controls width="100%" style="border-radius: 8px; box-shadow: 0 2px 8px #0002;"></video>

[✉️ Get notified when the packaged version releases](https://airunner.org/)

<table>
  <tr>
    <td valign="top" colspan="4">

  [![Discord](https://img.shields.io/discord/839511291466219541?color=5865F2&logo=discord&logoColor=white)](https://discord.gg/ukcgjEpc5f) ![GitHub](https://img.shields.io/github/license/Capsize-Games/airunner) [![PyPi](https://github.com/Capsize-Games/airunner/actions/workflows/pypi-dispatch.yml/badge.svg)](https://github.com/Capsize-Games/airunner/actions/workflows/pypi-dispatch.yml) ![GitHub last commit](https://img.shields.io/github/last-commit/Capsize-Games/airunner)
    
  </td></tr>
  <tr>
  <td valign="top">
    
**🐞 [Report Bug](https://github.com/Capsize-Games/airunner/issues/new?template=bug_report.md)**

</td>
  <td>

**✨ [Request Feature](https://github.com/Capsize-Games/airunner/issues/new?template=feature_request.md)**
    
  </td>
  <td>
    
**🛡️ [Report Vulnerability](https://github.com/Capsize-Games/airunner/security/policy)**
    
</td>
<td>
  
**🛡️ [Wiki](https://github.com/Capsize-Games/airunner/wiki)**

</td>
</tr>

</table>

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
| **🌐 Privacy-First Web Browser** |
| - Built-in secure browser with off-the-record profiles<br>- HTTPS-only enforcement & strict certificate validation<br>- RAG integration for web content analysis<br>- Text extraction & summarization tools<br>- Zero persistent tracking or data storage |
| **🔒 Privacy and Security** |
| - Runs locally, no external API (default)<br>- Customizable LLM guardrails & image safety<br>- Disables HuggingFace telemetry<br> - Restricts network access |
| **⚡ Performance & Utility** |
| - Fast generation (~2s on RTX 2080s)<br>- Docker-based setup & GPU acceleration<br>- Theming (Light/Dark/System)<br>- NSFW toggles<br>- Extension API<br>- Python library & API support |


### 🌍 Language Support

| Language         | TTS | LLM | STT | GUI |
|------------------|-------------|-------------|-------------|-------------|
| English          | ✅          | ✅          | ✅          | ✅          |
| Japanese         | ✅          | ✅          | ❌          | ✅          |
| Spanish          | ✅          | ✅          | ❌          | ❌          |
| French           | ✅          | ✅          | ❌          | ❌          |
| Chinese          | ✅          | ✅          | ❌          | ❌          |
| Korean           | ✅          | ✅          | ❌          | ❌          |

[🫰 Request language support](https://github.com/Capsize-Games/airunner/issues/new?template=language_support.md)
---

## 💾 Installation Quick Start

### ⚙️ System Requirements

| Specification       | Minimum                              | Recommended                          |
|---------------------|--------------------------------------------|--------------------------------------------|
| **OS** | Ubuntu 22.04, Windows 10                   | Ubuntu 22.04 (Wayland)                     |
| **CPU** | Ryzen 2700K or Intel Core i7-8700K         | Ryzen 5800X or Intel Core i7-11700K        |
| **Memory** | 16 GB RAM                                  | 32 GB RAM                                  |
| **GPU** | NVIDIA RTX 3060 or better                  | NVIDIA RTX 4090 or better                  |
| **Network** | Broadband (used to download models)        | Broadband (used to download models)        |
| **Storage** | 22 GB (with models), 6 GB (without models) | 100 GB or higher                           |


### 🔧 Installation Steps

1. **Install system requirements**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3-openssl git nvidia-cuda-toolkit pipewire libportaudio2 libxcb-cursor0 gnupg gpg-agent pinentry-curses espeak xclip cmake qt6-qpa-plugins qt6-wayland qt6-gtk-platformtheme mecab libmecab-dev mecab-ipadic-utf8 libxslt-dev mkcert
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
   ```
4. **Run AI Runner**
   ```bash
   airunner
   ```

For more options, including Docker, see the [Installation Wiki](https://github.com/Capsize-Games/airunner/wiki/Installation-instructions).

---

### Basic Usage

- **Run AI Runner**: `airunner`
- **Run the downloader**: `airunner-setup`
- **Build templates**: `airunner-build-ui`

---

## 🤖 Models

<table>
  <tr>
    <td valign="top">

**These are the sizes of the optional models that power AI Runner.**

| Modality         | Size |
|------------------|------|
| **Text-to-Speech** | |
| OpenVoice (Voice) | 4.0 GB |
| Speech T5 (Voice) | 654.4 MB |
| **Speech-to-Text** | |
| Whisper Tiny | 155.4 MB |
| **Text Generation** | |
| Ministral 8b (default) | 4.0 GB |
| Whisper Tiny | 155.4 MB |
| Ollama (various models) | 1.5 GB - 20 GB |
| OpenRouter (various models) | 1.5 GB - 20 GB |
| Huggingface (various models) | 1.5 GB - 20 GB |
| Ministral instruct 8b (4bit) | 5.8 GB |
| **Image Generation** | |
| Controlnet (SD 1.5) | 10.6 GB |
| Controlnet (SDXL) | 320.2 MB |
| Safety Checker + Feature Extractor | 3.2 GB |
| SD 1.5 | 1.6 MB |
| SDXL 1.0 | 6.45 MB |


## Stack

AI Runner uses the following stack

- **SQLite**: For local data storage
- **Alembic**: For database migrations
- **SQLAlchemy**: For ORM
- **Pydantic**: For data validation
- **http.server**: Basic local server for static files
- **PySide6**: For the GUI
- A variety of other libraries for TTS, STT, LLMs, and image generation

</td>
<td valign="top">

<div style="border: 1px solid white; border-radius: 8px; margin-bottom: 10px; padding: 16px; background-color: #f9f9f9; box-shadow: 0 2px 8px #0002; background: transparent; max-width: 250px">

### ✨ LLM Vendors

- **Default local model:** Ministral 8b instruct 4bit
- **Ollama:**: A variety of local models to choose from (requires Ollama CLI)
- **OpenRouter**: Remove server-side LLMs (requires API key)
- **Huggingface**: Coming soon

</div>

<div style="border: 1px solid white; border-radius: 8px; margin-bottom: 10px; padding: 16px; background-color: #f9f9f9; box-shadow: 0 2px 8px #0002; background: transparent; max-width: 250px">

### 🎨 Art Models

By default, AI Runner installs essential TTS/STT and minimal LLM components, but AI art models must be supplied by the user.

Organize them under your local AI Runner data directory:

```plaintext
~/.local/share/airunner
├── art
│   └── models
│       ├── SD 1.5
│       │   ├── controlnet
│       │   ├── embeddings
│       │   ├── inpaint
│       │   ├── lora
│       │   └── txt2img
│       ├── Flux (not supported yet)
│       ├── SDXL 1.0
│       │   ├── controlnet
│       │   ├── embeddings
│       │   ├── inpaint
│       │   ├── lora
│       │   └── txt2img
│       └── SDXL Turbo
│           ├── controlnet
│           ├── embeddings
│           ├── inpaint
│           ├── lora
│           └── txt2img
```

</div>

### Optional third-party services

- **OpenStreetMap:** Map API
- **OpenMeteo:** Weather API

</td>
</tr>

</table>

---

## Chatbot Mood and Conversation Summary System

- The chatbot's mood and conversation summary system is always enabled by default. The bot's mood and emoji are shown with each bot message.
- When the LLM is updating the bot's mood or summarizing the conversation, a loading spinner and status message are shown in the chat prompt widget. The indicator disappears as soon as a new message arrives.
- This system is automatic and requires no user configuration.
- For more details, see the [LLM Chat Prompt Widget README](src/airunner/gui/widgets/llm/README.md).
- The mood and summary engines are now fully integrated into the agent runtime. When the agent updates mood or summarizes the conversation, it emits a signal to the UI with a customizable loading message. The chat prompt widget displays this message as a loading indicator.
- See `src/airunner/handlers/llm/agent/agents/base.py` for integration details and `src/airunner/api/chatbot_services.py` for the API function.

## 🔍 Aggregated Search Tool

AI Runner includes an Aggregated Search Tool for querying multiple online services from a unified interface. This tool is available as a NodeGraphQt node, an LLM agent tool, and as a Python API.

**Supported Search Services:**
- DuckDuckGo (no API key required)
- Wikipedia (no API key required)
- arXiv (no API key required)
- Google Custom Search (requires `GOOGLE_API_KEY` and `GOOGLE_CSE_ID`)
- Bing Web Search (requires `BING_SUBSCRIPTION_KEY`)
- NewsAPI (requires `NEWSAPI_KEY`)
- StackExchange (optional `STACKEXCHANGE_KEY` for higher quota)
- GitHub Repositories (optional `GITHUB_TOKEN` for higher rate limits)
- OpenLibrary (no API key required)

**API Key Setup:**
- Set the required API keys as environment variables before running AI Runner. Only services with valid keys will be queried.
- Example:
  ```bash
  export GOOGLE_API_KEY=your_google_api_key
  export GOOGLE_CSE_ID=your_google_cse_id
  export BING_SUBSCRIPTION_KEY=your_bing_key
  export NEWSAPI_KEY=your_newsapi_key
  export STACKEXCHANGE_KEY=your_stackexchange_key
  export GITHUB_TOKEN=your_github_token
  ```

**Usage:**
- Use the Aggregated Search node in NodeGraphQt for visual workflows.
- Call the tool from LLM agents or Python code:
  ```python
  from airunner.tools.search_tool import AggregatedSearchTool
  results = await AggregatedSearchTool.aggregated_search("python", category="web")
  ```
- See `src/airunner/tools/README.md` for more details.

**Note:**
- DuckDuckGo, Wikipedia, arXiv, and OpenLibrary do not require API keys and can be used out-of-the-box.
- For best results and full service coverage, configure all relevant API keys.

---

## 🔒 Enabling HTTPS for the Local HTTP Server

AI Runner's local server enforces HTTPS-only operation for all local resources. HTTP is never used or allowed for local static assets or API endpoints. At startup, the server logs explicit details about HTTPS mode and the certificate/key in use. Security headers are set and only GET/HEAD methods are allowed for further hardening.

### How to Enable SSL/TLS (HTTPS)

1. **Automatic Certificate Generation (Recommended):**
   - By default, AI Runner will auto-generate a self-signed certificate in `~/.local/share/airunner/certs/` if one does not exist. No manual steps are required for most users.
   - If you want to provide your own certificate, place `cert.pem` and `key.pem` in the `certs` directory under your AI Runner base path.

2. **Manual Certificate Generation (Optional):**
   - You can manually generate a self-signed certificate with:
     ```bash
     airunner-generate-cert
     ```
   - This will create `cert.pem` and `key.pem` in your current directory. Move them to your AI Runner certs directory if you want to use them.

3. **Configure AI Runner to Use SSL:**
   - The app will automatically use the certificates in the certs directory. If you want to override, set the environment variables:
     ```bash
     export AIRUNNER_SSL_CERT=~/path/to/cert.pem
     export AIRUNNER_SSL_KEY=~/path/to/key.pem
     airunner
     ```
   - The server will use HTTPS if both files are provided.

4. **Access the App via `https://localhost:<port>`**
   - The default port is 5005 (configurable in `src/airunner/settings.py`).
   - Your browser may warn about the self-signed certificate; you can safely bypass this for local development.

### Security Notes
- **For production or remote access, use a certificate from a trusted CA.**
- **Never share your private key (`key.pem`).**
- The server only binds to `127.0.0.1` by default for safety.
- For additional hardening, see the [Security](SECURITY.md) guide and the code comments in `local_http_server.py`.

### 🔑 Generate a Self-Signed Certificate (airunner-generate-cert)

You can generate a self-signed SSL certificate for local HTTPS with a single command:

```bash
airunner-generate-cert
```

This will create `cert.pem` and `key.pem` in your current directory. Use these files with the local HTTP server as described above.

See the [SSL/TLS section](#🔒-enabling-https-for-the-local-http-server) for full details.

### Additional Requirements for Trusted Local HTTPS

- For a browser-trusted local HTTPS experience (no warnings), install [mkcert](https://github.com/FiloSottile/mkcert):
  ```bash
  # On Ubuntu/Debian:
  sudo apt install libnss3-tools
  brew install mkcert   # (on macOS, or use your package manager)
  mkcert -install
  ```
- If `mkcert` is not installed, AI Runner will fall back to OpenSSL self-signed certificates, which will show browser warnings.
- See the [SSL/TLS section](#🔒-enabling-https-for-the-local-http-server) for details.

---

## Contributing

We welcome pull requests for new features, bug fixes, or documentation improvements. You can also build and share **extensions** to expand AI Runner’s functionality. For details, see the [Extensions Wiki](https://github.com/Capsize-Games/airunner/wiki/Extensions).

Take a look at the [Contributing document](https://github.com/Capsize-Games/airunner/CONTRIBUTING.md) and the [Development wiki page](https://github.com/Capsize-Games/airunner/wiki/Development) for detailed instructions.

## 🧪 Testing & Test Organization

AI Runner uses `pytest` for all automated testing. Test coverage is a priority, especially for utility modules.

### Test Directory Structure
- **Headless-safe tests:**
  - Located in `src/airunner/utils/tests/`
  - Can be run in any environment (including CI, headless servers, and developer machines)
  - Run with:
    ```bash
    pytest src/airunner/utils/tests/
    ```
- **Display-required (Qt/Xvfb) tests:**
  - Located in `src/airunner/utils/tests/xvfb_required/`
  - Require a real Qt display environment (cannot be run headlessly or with `pytest-qt`)
  - Typical for low-level Qt worker/signal/slot logic
  - Run with:
    ```bash
    xvfb-run -a pytest src/airunner/utils/tests/xvfb_required/
    # Or for a single file:
    xvfb-run -a pytest src/airunner/utils/tests/xvfb_required/test_background_worker.py
    ```
  - See the [README in xvfb_required/](src/airunner/utils/tests/xvfb_required/README.md) for details.

### CI/CD
- By default, only headless-safe tests are run in CI.
- Display-required tests are intended for manual or special-case runs (e.g., when working on Qt threading or background worker code).
- (Optional) You may automate this split in CI by adding a separate job/step for xvfb tests.

### General Testing Guidelines
- All new utility code must be accompanied by tests.
- Use `pytest`, `pytest-qt` (for GUI), and `unittest.mock` for mocking dependencies.
- For more details on writing and organizing tests, see the [project coding guidelines](#copilot-instructions-for-ai-runner-project) and the `src/airunner/utils/tests/` folder.

## Development & Testing

- Follow the [copilot-instructions.md](.github/copilot-instructions.md) for all development, testing, and contribution guidelines.
- Always use the `airunner` command in the terminal to run the application.
- Always run tests in the terminal (not in the workspace test runner).
- Use `pytest` and `pytest-cov` for running tests and checking coverage.
- UI changes must be made in `.ui` files and rebuilt with `airunner-build-ui`.

## Documentation

- See the [Wiki](https://github.com/Capsize-Games/airunner/wiki) for architecture, usage, and advanced topics.

## Module Documentation

- [API Service Layer](src/airunner/api/README.md)
- [Main Window Model Load Balancer](src/airunner/gui/windows/main/README.md)
- [Facehugger Shield Suite](src/airunner/facehuggershield/README.md)
- [NodeGraphQt Vendor Module](src/airunner/vendor/nodegraphqt/README.md)
- [Xvfb-Required Tests](src/airunner/utils/tests/xvfb_required/README.md)
- [ORM Models](src/airunner/data/models/README.md)

For additional details, see the [Wiki](https://github.com/Capsize-Games/airunner/wiki).
