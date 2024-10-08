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

# AI RUNNER 

---

## Run AI models on your own hardware 

### Stable Diffusion

![img.png](img.png)

### Customizable Chatbots with Moods and Personalities

![img_1.png](img_1.png)

---

## ⭐ Features

AI Runner is an AI interface which allows you to run open-source 
large language models (LLM) and AI image generators (Stable Diffusion) on your own hardware.

| Feature                                | Description                                              |
|----------------------------------------|----------------------------------------------------------|
| 🗣️ **LLMs and communication**         |
| ✅ Voice-based chatbot conversations    | Have conversations with a chatbot using your voice       |
| ✅ Text-to-speech                       | Convert text to spoken audio                             |
| ✅ Speech-to-text                       | Convert spoken audio to text                             |
| ✅ Customizable chatbots with LLMs      | Generate text using large language models                |
| ✅ RAG on local documents and websites  | Interact with your local documents using an LLM          |
| 🎨 **Image Generation**                |
| ✅ Stable Diffusion (all versions)      | Generate images using Stable Diffusion                   |
| ✅ Drawing tools                        | Turn sketches into art                                   |
| ✅ Text-to-Image                        | Generate images from textual descriptions                |
| ✅ Image-to-Image                       | Generate images based on input images                    |
| 🖼️ **Image Manipulation**             |
| ✅ Inpaint and Outpaint                 | Modify parts of an image while maintaining context       |
| ✅ Controlnet                           | Control image generation with additional input           |
| ✅ LoRA                                 | Efficiently fine-tune models with LoRA                   |
| ✅ Textual Embeddings                   | Use textual embeddings for image generation control      |
| ✅ Image Filters                        | Blur, film grain, pixel art and more                     |
| 🔧 **Utility**                         |
| ✅ Run offline, locally                 | Run on your own hardware without internet                |
| ✅ Fast generation                      | Generate images in ~2 seconds (RTX 2080s)                |
| ✅ Run multiple models at once          | Utilize multiple models simultaneously                   |
| ✅ Dark mode                            | Comfortable viewing experience in low-light environments |
| ✅ Infinite scrolling canvas            | Seamlessly scroll through generated images               |
| ✅ NSFW filter toggle                   | Help control the visibility of NSFW content              |
| ✅ NSFW guardrails toggle               | Help prevent generation of LLM harmful content           |
| ✅ Fully customizable                   | Easily adjust all parameters                             |
| ✅ Fast load time, responsive interface | Enjoy a smooth and responsive user experience            |
| ✅ Pure python                          | No reliance on a webserver, pure python implementation   |

---

## 💻 System Requirements

#### Minimum system requirements

- OS: Linux
- Processor: Intel i5 or equivalent
- Memory: 16 GB RAM
- Graphics: 2080s RTX or higher
- Network: Broadband Internet connection required for setup
- Storage: 130 GB available space

#### Recommended system specs

- OS: Linux
- Processor: Intel i7 or equivalent
- Memory: 30 GB RAM
- Graphics: 4090 RTX or higher
- Network: Broadband Internet connection required for setup
- Storage: 130 GB available space

---

## 🔧 Installation

### Linux

Install prerequisites

```bash
sudo apt update
sudo apt install -y fonts-noto-color-emoji
sudo apt install -y libportaudio2
sudo apt install -y libxcb-cursor0
sudo apt install -y espeak
sudo apt install -y xclip
sudo apt install -y git
sudo apt install -y python3-pip
sudo apt install -y python3.10-venv
```

Clone the repository

```bash
git clone https://github.com/Capsize-Games/airunner.git
cd airunner
```

Create a virtual environment

```bash
python3 -m venv airunner
source airunner/bin/activate
```

Install AI Runner

```bash
pip install -e .
```

---

## 🚀 Running AI Runner

### Linux

Activate the virtual environment

```bash
source airunner/bin/activate
```

Run AI Runner

```bash
cd airunner/src/airunner
./main.py
```

---

### Privacy and Security

Although AI Runner v3.0 is built with Huggingface libraries, we have taken
care to strip the application of any telemetry or tracking features.

---

### Internet access

Only the setup wizard needs access to the internet in order to download the required models.

For more information see the [Darklock](https://github.com/capsize-games/darklock)  and
[Facehuggershield](https://github.com/capsize-games/facehuggershield) libraries.

---

### Disc access

Write access for the transformers library has been disabled, preventing it from creating a huggingface 
cache directory at runtime.

The application itself may still access the disc for reading and writing, however we have restricted
reads and writes to the user provided `airunner` directory (by default this is located at `~/.local/share/airunner`).

All other attempts to access the disc are blocked and logged for your review.

For more information see `src/security/restrict_os_access.py`.

---

### Huggingface Hub

The Huggingface Hub is installed so that Transformers, Diffusers and other Huggingface libraries
will continue to function as expected, however it has been neutered to prevent it from accessing 
the internet.

The security measures taken for this library are as follows

- Prevented from accessing the internet
- Prevented from accessing the disc
- All environment variables set for maximum security
- All telemetry disabled

See [Facehuggershield](https://github.com/capsize-games/facehuggershield) for more information.
