[![Banner](banner.png)](https://capsizegames.itch.io/ai-runner)
[![Upload Python Package](https://github.com/Capsize-Games/airunner/actions/workflows/python-publish.yml/badge.svg)](https://github.com/Capsize-Games/airunner/actions/workflows/python-publish.yml)
[![Discord](https://img.shields.io/discord/839511291466219541?color=5865F2&logo=discord&logoColor=white)](https://discord.gg/PUVDDCJ7gz)
![GitHub](https://img.shields.io/github/license/Capsize-Games/airunner)
![GitHub last commit](https://img.shields.io/github/last-commit/Capsize-Games/airunner)
![GitHub issues](https://img.shields.io/github/issues/Capsize-Games/airunner)
![GitHub closed issues](https://img.shields.io/github/issues-closed/Capsize-Games/airunner)
![GitHub pull requests](https://img.shields.io/github/issues-pr/Capsize-Games/airunner)
![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed/Capsize-Games/airunner)

AI Runner allows you to run Stable Diffusion locally using your own hardware. It comes with drawing tools and an infinite canvas which lets you outpaint to any size you wish.


![img.png](img.png)

---

## [Download the official build on itch.io](https://capsizegames.itch.io/ai-runner)!

This is the compiled version of AI Runner which you can use without installing any additional dependencies.

---

## Pypi installation

If you would like to use AI Runner as a library, follow this method of installation.
Currently there isn't much of an external API so using AI Runner as a library is not recommended.

### Prerequisites

- Ubuntu 20.04+ or Windows 10+
- Python 3.10.6
- pip-23.0.1

Windows
```
pip install torch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1 --index-url https://download.pytorch.org/whl/cu117
pip install aihandlerwindows
pip install https://github.com/w4ffl35/diffusers/archive/refs/tags/v0.14.0.ckpt_fix.tar.gz
pip install https://github.com/w4ffl35/transformers/archive/refs/tags/tensor_fix-v1.0.2.tar.gz
pip install https://github.com/acpopescu/bitsandbytes/releases/download/v0.37.2-win.0/bitsandbytes-0.37.2-py3-none-any.whl
pip install airunner --no-deps
```

Linux
```
pip install https://github.com/w4ffl35/diffusers/archive/refs/tags/v0.14.0.ckpt_fix.tar.gz
pip install https://github.com/w4ffl35/transformers/archive/refs/tags/tensor_fix-v1.0.2.tar.gz
pip install airunner
```

---

## Using AI Runner

Type what you would like to see int the prompt textbox. Type what you would like to guide the generator away from
in the negative prompt textbox. Click the "Generate" button to generate an image. Adjust settings as you see fit.

---

### Model support

Stable Diffusion v1 and v2 models are supported in the following formats

#### File formats

- Diffusers
- Safetensors
- ckpt files
- Textual Inversion embeddings

#### Models

- txt2txt
- img2img
- txt2pix
- inpaint / outpaint
- controlnet

---

### Custom models

1. Place your custom models in a folder of your choice, for example `~/stablediffusion`
2. If you have textual embeddings place them in `~/<your_folder>/embeddings`
2. Start the app and navigate to settings > preferences
3. Add the absolute path to the folder you chose to store your models in
4. Click OK and restart the app

---

### Keyboard / Mouse controls

The following are some previous undocumented features

Misc
- `hold middle mouse + drag` - Pan the canvas

With the brush tool selected:
- `hold left or right mouse and drag` - Draw on the canvas

With the eraser tool selected:
- `hold left or right mouse and drag` - Erase on the canvas

With the active grid area tool selected:
- `hold ctrl or shift and scroll up or down` - Changes the width and height of the active grid area