[![Banner](banner.png)](https://capsizegames.itch.io/ai-runner)
[![Upload Python Package](https://github.com/Capsize-Games/airunner/actions/workflows/python-publish.yml/badge.svg)](https://github.com/Capsize-Games/airunner/actions/workflows/python-publish.yml)
![GitHub](https://img.shields.io/github/license/Capsize-Games/airunner)
![GitHub last commit](https://img.shields.io/github/last-commit/Capsize-Games/airunner)
![GitHub issues](https://img.shields.io/github/issues/Capsize-Games/airunner)
![GitHub closed issues](https://img.shields.io/github/issues-closed/Capsize-Games/airunner)
![GitHub pull requests](https://img.shields.io/github/issues-pr/Capsize-Games/airunner)
![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed/Capsize-Games/airunner)

AI Runner allows you to run Stable Diffusion locally using your own hardware. It comes with drawing tools and an infinite canvas which lets you outpaint to any size you wish.

![img.png](img.png)

---

## Bundled Installation

[Official Build can be acquired here](https://capsizegames.itch.io/ai-runner) for those who want to use a compiled version of AI Runner without having to install any additional requirements

---

## Development

### Prerequisites

- Ubuntu 20.04+ or Windows 10+
- Python 3.10.6
- pip-23.0.1

#### Pypi installation

- `pip install airunner`
- `pip install git+https://github.com/w4ffl35/diffusers.git@ckpt_fix`
- `pip install git+https://github.com/w4ffl35/transformers.git@tensor_fix`

#### Development installation

Use this installation method if you intend to modify the source code of Chat AI.

- Ubuntu 20.04+ or Windows 10+
- Python 3.10.6
- pip-23.0.1

1. Fork this repo on github
2. Clone it
3. `cd airunner && pip install -r requirements.txt`
4. `cd sdrunner && python main.py`
