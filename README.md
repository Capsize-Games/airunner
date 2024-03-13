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

---

![Screenshot from 2023-06-30 10-43-49](https://github.com/Capsize-Games/airunner/assets/25737761/72e0dd26-53ca-4d5c-8f07-b6327a59b50c)

## 🔧 Installation

### Compiled

[Download the official build on itch.io](https://capsizegames.itch.io/ai-runner)!

This is the compiled version of AI Runner which you can use without 
installing any additional dependencies.

### PyPi and Source

#### Linux

```bash
sudo apt update
sudo apt install airunner
```

#### Windows

```bash
pip install pypiwin32
```

#### PyPi

If you want to install AI Runner using pip, you can do so using the following command:

```bash
pip install airunner
```

#### Source

If you want to install AI Runner from source, you can do so using the following command:

```bash
git clone -b develop https://github.com/Capsize-Games/airunner.git
cd airunner && pip install -e .
```
Run it with

```bash
cd src/airunner
python main.py
```

[See the installation 
wiki page for more information](https://github.com/Capsize-Games/airunner/wiki/Installation-instructions)

---

## ⭐ Features

AI Runner is a multi-modal AI application which allows you to run open-source 
large language models and AI image generators on your own hardware.

- Have conversations with with a chatbot using your voice
- Text-to-speech
- Speech-to-text
- Vision-to-text
- Text generation with large language models (LLMs)
- Image generation using Stable Diffusion and Kandinsky
- Draw and generate images in near real-time
- Run multiple models at once
- Easy setup - download and run. No need to install any requirements*
- Run offline, locally on your own hardware!
- Fast! Generate images in approximately 2 seconds using an RTX 2080s, 512x512 dimensions, 20 steps euler_a (approximately 10 seconds for 512x512 20 steps Euler A on 1080gtx). Also runs on CPU†
- text-to-image
- image-to-image
- inpaint and outpaint
- pix2pix
- depth2img
- controlnet
- LoRA
- textual embeddings
- Drawing tools
- Image filters
- Dark mode
- Infinite scrolling canvas - use outpainting to create artwork at any size you wish or expand existing images.
- NSFW filter toggle
- Standard Stable Diffusion settings
- Fast load time, responsive interface
- Pure python - does not rely on a webserver

### Requirements

- Cuda capable GPU (RTX 2080s or higher recommended)
- At least 8gb of RAM
- at least 5.8gb of disc space to install AI Runner

The core AI Runner  program takes approximately 5.8gb of disc space to install, however the size of each model varies. 
Typically models are between 2.5gb to 8gb in size. The more models you download, the more disc space you will need.

---

## Using AI Runner

[Instructions on how to use AI Runner can be found in the wiki](https://github.com/Capsize-Games/airunner/wiki/AI-Runner)

---

### Unit tests

Unit tests can be run using the following command:

**All tests:**
`python -m unittest discover tests`

**Individual test:**
`python -m unittest tests.test_canvas`

---

### Build the code

First install PyInstaller

```bash
pip install pyinstaller
```

Then run the build script

```bash
bash build.dev.sh
```

---

### release_debian_ppa.sh

This is a bash script that automates the process of packaging a Python project into a Debian package and uploading it to a Personal Package Archive (PPA). Here's a step-by-step breakdown of what the script does:

1. Extracts the version of the Python project (named `airunner`) from the `setup.py` file. This is done by running a Python command that imports the `run_setup` function from `distutils.core`, runs the `setup.py` file, and prints the version.
2. Prompts the user to enter the Debian version and a commit message.
3. Creates a temporary `.gitignore` file that does not include the `dist` directory. This is done by running the `grep` command with the `-v` option, which inverts the matching, so it matches lines that do not contain `dist`.
4. Creates a tarball (archive file) of the current directory, excluding version control system directories and files specified in the temporary `.gitignore` file. The tarball is named `airunner_$AIRUNNER_VERSION.orig.tar.gz` and is placed in the parent directory.
5. Removes the temporary `.gitignore` file.
6. Updates the Debian changelog file with the new version and the commit message. This is done by running the `dch` command with the `-v` option to specify the version and the `-D` option to specify the distribution.
7. Builds the Debian source package. This is done by running the `dpkg-buildpackage` command with the `-S` option to build a source package, the `-D` option to check build dependencies and conflicts, and the `-sa` option to include the original source.
8. Changes the current directory to the parent directory.
9. Uploads the Debian source package to the PPA. This is done by running the `dput` command with the PPA and the source package as arguments.

Currently we are only releasing under a dev PPA, but we will switch to a stable PPA in the future.