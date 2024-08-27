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

## v3.0.0.devX

AI Runner can be compiled with `pyinstaller` however the current version
is not yet stable (check the releases for stable versions).

Version 3.0 is a major upgrade which aims to move the application out of
prototype stage and into a more stable and user-friendly state.

It comes with a new UI, new features, and a more robust codebase, security
updates, and a more streamlined installation process and much more.

We plan to release future distributions via Snap on Linux.

See `Privacy and Security` for more information.

---

## Stable Diffusion on your own hardware 


![img_3.png](img.png)

---

## ⭐ Features

AI Runner is a multi-modal AI interface which allows you to run open-source 
large language models and AI image generators on your own hardware.

| Feature                                           | Description                                              |
|---------------------------------------------------|----------------------------------------------------------|
| 🗣️ **LLMs and communication**                    |
| ✅ Voice-based chatbot conversations               | Have conversations with a chatbot using your voice       |
| ✅ Text-to-speech                                  | Convert text to spoken audio                             |
| ✅ Speech-to-text                                  | Convert spoken audio to text                             |
| ✅ Vision-to-text                                  | Extract text from images                                 |
| ✅ Text generation with LLMs                       | Generate text using large language models                |
| ✅ RAG on local documents and websites             | Interact with your local documents using an LLM          |
| 🎨 **Image Generation**                           |
| ✅ Stable Diffusion (all versions)                 | Generate images using Stable Diffusion                   |
| 🔜 Kandinsky                                      | Generate images using Kandinsky                          |
| ✅ Near Real-Time Drawing                          | Draw and generate images in near real-time               |
| ✅ Text to Image (aka TextToImage / Txt2Img)       | Generate images from textual descriptions                |
| ✅ Image to Image (aka ImageToImage / Image2Image) | Generate images based on input images                    |
| 🖼️ **Image Manipulation**                        |
| ✅ Inpaint and Outpaint                            | Modify parts of an image while maintaining context       |
| ✅ Pix2Pix                                         | Transform images from one domain to another              |
| ✅ Depth to Image (aka DepthToImage / Depth2Img)   | Generate images from depth maps                          |
| ✅ Controlnet                                      | Control image generation with additional input           |
| ✅ LoRA                                            | Efficiently fine-tune models with LoRA                   |
| ✅ Textual Embeddings                              | Use textual embeddings for image generation control      |
| 🔜 Upscale with GFPGAN                            | Use textual embeddings for image generation control      |
| 🔧 **Utility**                                    |
| ✅ Run offline, locally                            | Run on your own hardware without internet                |
| ✅ Fast generation                                 | Generate images in ~2 seconds (RTX 2080s)                |
| ✅ Run multiple models at once                     | Utilize multiple models simultaneously                   |
| ✅ Drawing tools                                   | Built-in tools for drawing and image manipulation        |
| ✅ Image filters                                   | Apply various filters to images                          |
| ✅ Dark mode                                       | Comfortable viewing experience in low-light environments |
| ✅ Infinite scrolling canvas                       | Seamlessly scroll through generated images               |
| ✅ NSFW filter toggle                              | Help control the visibility of NSFW content              |
| ✅ NSFW guardrails                                 | Help prevent generation of harmful content               |
| ✅ Standard Stable Diffusion settings              | Easily adjust standard Stable Diffusion parameters       |
| ✅ Fast load time, responsive interface            | Enjoy a smooth and responsive user experience            |
| ✅ Pure python                                     | No reliance on a webserver, pure python implementation   |

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

### Linux

1. Open your file explorer and navigate to the directory containing the `install.sh` script
2. Open the terminal using the keyboard shortcut `Ctrl + Alt + T`
3. Drag the `install.sh` script into the terminal and press `Enter`
4. Follow the on-screen instructions

---

## 🚀 Running AI Runner

### Linux

1. Open the terminal using the keyboard shortcut `Ctrl + Alt + T`
2. Navigate to the directory containing the `run.sh` script (`cd ~/airunner` for example)
3. Run the `bin/run.sh` script by typing `./bin/run.sh` and pressing `Enter`
4. AI Runner will start and you can begin using it after following the on-screen setup instructions

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
---

### Privacy and Security

Although AI Runner v3.0 is built with Huggingface libraries, we have taken
care to strip the application of any telemetry or tracking features.

The main application itself is unable to access the internet, and we are working
towards properly sandboxing certain features to ensure user privacy and security.

As this application evolves we will migrate away from the Huggingface libraries.

### Internet access

The core application is incapable of accessing the internet. However there are two features which require
internet access. These two features are the `setup wizard` and the `model manager`.

Each of these tools are isolated in their own application windows
which are capable of directly accessing and downloading files on Huggingface.co and 
civitai.com (depending on the given URL). Any other URL will be blocked.

The Huggingface Hub library is not used to access these downloads.

For more information see the [Darklock](https://github.com/capsize-games/darklock)  and
[Facehuggershield](https://github.com/capsize-games/facehuggershield) libraries.

---

### Disc access

Write access for the transformers library has been disabled, preventing it from creating a huggingface 
cache directory at runtime.

The application itself may still access the disc for reading and writing, however we have restricted
reads and writes to the user provided `airunner` directory (by default this is located at `~/.airunner`).

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

---

#### Planned security measures for Huggingface Libraries

We plant o remove the Huggingface libraries from the application in the future.
Although the architecture is currently dependent on these libraries, we will
migrate to a better solution in the future.
