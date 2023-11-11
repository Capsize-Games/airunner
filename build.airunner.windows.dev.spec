# -*- mode: python ; coding: utf-8 -*-
import os
import sys ; sys.setrecursionlimit(sys.getrecursionlimit() * 5)
os.environ["PATH"] = "C:\\;C:\\Program Files\\NVIDIA\\CUDNN\\v8.6.0.163\\bin;C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v11.7\\bin;C:\\Python310;C:\\Python310\\site-packages;C:\\Python310\\site-packages\\lib;C:\\Python310\\Scripts;%PATH%"
import shutil
from PyInstaller.utils.hooks import copy_metadata, collect_data_files
os.environ["AIRUNNER_ENVIRONMENT"] = "prod"
os.environ["DEV_ENV"] = "0"
os.environ["PYTHONOPTIMIZE"] = "0"
block_cipher = None
ROOT = "."
DIST = "./dist/airunner"
os.environ["AIRUNNER_ENVIRONMENT"] = "prod"
DEBUGGING = True
EXCLUDE_BINARIES = False
EXE_NAME = "airunner"  # used when creating a binary instead of a folder
EXE_STRIP = False
EXE_UPX = True
EXE_RUNTIME_TMP_DIR = None
COLLECT_NAME = 'airunner'
COLLECT_STRIP = False
COLLECT_UPX = True

datas = []
datas += copy_metadata('tqdm')
datas += copy_metadata('regex')
datas += copy_metadata('requests')
datas += copy_metadata('packaging')
datas += copy_metadata('filelock')
datas += copy_metadata('numpy')
datas += copy_metadata('tokenizers')
datas += copy_metadata('transformers')
datas += copy_metadata('rich')
datas += copy_metadata('sympy')
datas += copy_metadata('tensorflow')
datas += copy_metadata('scipy')
datas += collect_data_files("torch", include_py_files=True)
datas += collect_data_files("torchvision", include_py_files=True)
datas += collect_data_files("JIT", include_py_files=True)
datas += collect_data_files("pytorch_lightning", include_py_files=True)
datas += collect_data_files("lightning_fabric", include_py_files=True)
datas += collect_data_files("transformers", include_py_files=True)
datas += collect_data_files("tensorflow", include_py_files=True)
datas += collect_data_files("sympy", include_py_files=True)
datas += collect_data_files("controlnet_aux", include_py_files=True)
a = Analysis(
    [
        f'{ROOT}\\src\\airunner\\main.py',
    ],
    pathex=[
        ".\\venv\\Lib\\site-packages",
        ".\\venv\\Lib\\site-packages\\tokenizers",
        ".\\venv\\Lib\\site-packages\\tensorflow_io_gcs_filesystem\\core\\python\\ops",
        ".\\venv\\Lib\\site-packages\\tensorflow\\python\\data\\experimental\\service\\",
        ".\\venv\\Lib\\site-packages\\torch\\lib",
        ".\\venv\\Lib\\site-packages\\PyQt6",
        # "C:\\Users\\root\\AppData\\Local\\Programs\\Python\\Python310\\Lib\\site-packages\\tensorflow\\python\\data\\experimental\\service\\",
        # "C:\\Users\\root\\AppData\\Local\\Programs\\Python\\Python310\\",
    ],
    binaries=[
        (".\\venv\\Lib\\site-packages\\torchvision\\cudart64_110.dll", "."),
        (".\\venv\\Lib\\site-packages\\PyQt6\\Qt6\\bin\\vcruntime140.dll", "."),
        (".\\venv\\Lib\\site-packages\\PyQt6\\Qt6\\bin\\vcruntime140_1.dll", "."),
        (".\\venv\\Lib\\site-packages\\PyQt6\\Qt6\\bin\\msvcp140.dll", "."),
        # ("C:\\api-ms-win-shcore-scaling-l1-1-1.dll.so", "."),
        (".\\venv\\Lib\\site-packages\\tensorflow\\python\\util\\_pywrap_utils.pyd", "."),
    ],
    datas=datas,
    hiddenimports=[
        "airunner",
        "airunner.extensions",
        "JIT",
        "accelerate",
        "google-auth",
        "google-auth-oauthlib",
        "google-pasta",
        "tqdm",
        "diffusers",
        "transformers",
        "torch",
        "torchvision",
        "torchvision.io",
        "logging",
        "logging.config",
        "einops",
        "omegaconf",
        "contextlib",
        "itertools",
        "pytorch_lightning",
        "huggingface_hub.hf_api",
        "huggingface_hub.repository",
        "inspect",
        "psutil",
        "matplotlib",
        "scipy",
        "sympy",
        "pywin32",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tcl",
        "tcl8",
        "cmake",
        "cryptography",
        "email-validator",
        "Jinja2",
        "lightning-cloud",
        "Markdown",
        "markdown-it-py",
        "MarkupSafe",
        "mdurl",
        "ninja",
        "nvidia-pyindex",
        "pytz",
        "tensorboard",
        "tensorboard-data-server",
        "tensorboard-plugin-wit",
        "unattended-upgrades",
        "watchfiles",
        "wcwidth",
        "websocket-client",
        "websockets",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=EXCLUDE_BINARIES,
    name=EXE_NAME,
    debug=DEBUGGING,
    strip=EXE_STRIP,
    upx=EXE_UPX,
    runtime_tmpdir=EXE_RUNTIME_TMP_DIR,
    console=DEBUGGING,
    bootloader_ignore_signals=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=COLLECT_STRIP,
    name=COLLECT_NAME,
    onefile=False,
    onedir=True,
    upx_dir="C:\\Python310\\Scripts\\",
)
shutil.copytree(
    f'{ROOT}/src/airunner/pyqt',
    f'{DIST}/pyqt'
)
shutil.copyfile(
    f'{ROOT}/windows.itch.toml',
    f'{DIST}/.itch.toml'
)
shutil.copytree(
    f'{ROOT}/src/airunner/src/icons',
    f'{DIST}/src/icons'
)
shutil.copytree(
    f'{ROOT}/src/airunner/data',
    f'{DIST}/data'
)
shutil.copyfile(
    f'{ROOT}/src/airunner/src/icon_256.png',
    f'{DIST}/src/icon_256.png'
)
shutil.copyfile(
    f'{ROOT}/src/airunner/images/splashscreen.png',
    f'{DIST}/images/splashscreen.png'
)
shutil.copyfile(
    f'{ROOT}/src/airunner/v1.yaml',
    f'{DIST}/v1.yaml'
)
shutil.copyfile(
    f'{ROOT}/src/airunner/v2.yaml',
    f'{DIST}/v2.yaml'
)
shutil.copyfile(
    f'{ROOT}/src/airunner/sd_xl_base.yaml',
    f'{DIST}/sd_xl_base.yaml'
)
shutil.copyfile(
    f'{ROOT}/src/airunner/sd_xl_refiner.yaml',
    f'{DIST}/sd_xl_refiner.yaml'
)
shutil.copyfile(
    f'.\\setup.py',
    f'{DIST}/setup.py'
)