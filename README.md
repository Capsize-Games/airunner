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

| Feature                                           | Description                                              |
|---------------------------------------------------|----------------------------------------------------------|
| 🗣️ **Communication**                             |
| ✅ Voice-based chatbot conversations               | Have conversations with a chatbot using your voice       |
| ✅ Text-to-speech                                  | Convert text to spoken audio                             |
| ✅ Speech-to-text                                  | Convert spoken audio to text                             |
| ✅ Vision-to-text                                  | Extract text from images                                 |
| ✅ Text generation with LLMs                       | Generate text using large language models                |
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