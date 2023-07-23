# -*- mode: python ; coding: utf-8 -*-
import os
import shutil
from PyInstaller.utils.hooks import copy_metadata, collect_data_files
import sys ; sys.setrecursionlimit(sys.getrecursionlimit() * 5)
os.environ["AIRUNNER_ENVIRONMENT"] = "prod"
libraries = [
    "/usr/lib/x86_64-linux-gnu/wine-development/",
    "./venv/lib/python3.10/site-packages/h5py.libs/",
    "./venv/lib/python3.10/site-packages/scipy.libs/",
    "./venv/lib/python3.10/site-packages/tokenizers.libs/",
    "./venv/lib/python3.10/site-packages/Pillow.libs/",
    "./venv/lib/python3.10/site-packages/opencv_python.libs/",
    "./venv/lib/python3.10/site-packages/torchaudio/lib/",
    "./venv/lib/python3.10/site-packages/torch/lib/",
    "/usr/lib/python3.10",
    "/usr/lib/x86_64-linux-gnu/",
    "/usr/local/lib/",
    "/usr/local/lib/python3.10",
    "/usr/local/lib/python3.10/dist-packages"
]
os.environ["LD_LIBRARY_PATH"] = ":".join(libraries)
block_cipher = None
DEBUGGING = True
EXCLUDE_BINARIES = True
EXE_NAME = "airunner-socket-server"  # used when creating a binary instead of a folder
EXE_STRIP = False
EXE_UPX = True
EXE_RUNTIME_TMP_DIR = None
COLLECT_NAME = 'airunner-socket-server'
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
datas += copy_metadata('opencv-python')
datas += collect_data_files("torch", include_py_files=True)
datas += collect_data_files("torchvision", include_py_files=True)
datas += collect_data_files("JIT", include_py_files=True)
datas += collect_data_files("pytorch_lightning", include_py_files=True)
datas += collect_data_files("lightning_fabric", include_py_files=True)
datas += collect_data_files("transformers", include_py_files=True)
datas += collect_data_files("sympy", include_py_files=True)
datas += collect_data_files("controlnet_aux", include_py_files=True)
a = Analysis(
    [
        f'./src/airunner/aihandler/socket_server.py',
    ],
    pathex=[
        "./venv/lib/python3.10/site-packages/",
        "./venv/lib/python3.10/site-packages/torch/lib",
        "./venv/lib/python3.10/site-packages/tokenizers",
        "./venv/lib/python3.10/site-packages/tensorflow",
        "/usr/lib/x86_64-linux-gnu/",
    ],
    binaries=[
        ('./venv/lib/python3.10/site-packages/nvidia/cudnn/lib/libcudnn_ops_infer.so.8', '.'),
        ('./venv/lib/python3.10/site-packages/nvidia/cudnn/lib/libcudnn_cnn_infer.so.8', '.'),
        ('/usr/lib/x86_64-linux-gnu/libgstgl-1.0.so.0', '.'),
    ],
    datas=datas,
    hiddenimports=[
        "JIT",
        "tqdm",
        "diffusers",
        "transformers",
        "nvidia",
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
        "numpy",
        "PIL._tkinter_finder",
        "sympy",
        "opencv-python",
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
        "google",
        "google-auth",
        "google-auth-oauthlib",
        "google-pasta",
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
    console=DEBUGGING
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=COLLECT_STRIP,
    upx=COLLECT_UPX,
    upx_exclude=[],
    name=COLLECT_NAME
)

# copy files for distribution
shutil.copytree('./src/airunner/data', './dist/airunner-socket-server/data')

# copy sd config files
os.makedirs('./dist/airunner/diffusers/pipelines/stable_diffusion', exist_ok=True)
shutil.copyfile('./src/airunner/v1.yaml', './dist/airunner-socket-server/v1.yaml')
shutil.copyfile('./src/airunner/v2.yaml', './dist/airunner-socket-server/v2.yaml')

shutil.copyfile(
    f'./venv/lib/python3.10/site-packages/JIT/__pycache__/random.cpython-310.pyc',
    f'./dist/airunner-socket-server/random.pyc'
)
