# -*- mode: python ; coding: utf-8 -*-
import os
import shutil
from PyInstaller.utils.hooks import copy_metadata, collect_data_files
import sys ; sys.setrecursionlimit(sys.getrecursionlimit() * 5)
os.environ["AIRUNNER_ENVIRONMENT"] = "prod"
libraries = [
    "/home/appuser/.local/lib/python3.10/site-packages/h5py.libs/",
    "/home/appuser/.local/lib/python3.10/site-packages/scipy.libs/",
    "/home/appuser/.local/lib/python3.10/site-packages/pillow.libs/",
    "/home/appuser/.local/lib/python3.10/site-packages/tokenizers.libs/",
    "/home/appuser/.local/lib/python3.10/site-packages/opencv_python_headless.libs/",
    "/home/appuser/.local/lib/python3.10/site-packages/torchaudio/lib/",
    "/home/appuser/.local/lib/python3.10/site-packages/torch/lib/",
    "/usr/lib/python3.10",
    "/usr/lib/x86_64-linux-gnu/",
    "/usr/local/lib/",
    "/usr/local/lib/python3.10/",
    "/usr/local/lib/python3.10/dist-packages",
    "/home/appuser/.local/lib/python3.10/site-packages/PySide6/Qt/plugins/platforms/",
    "/home/appuser/.local/lib/python3.10/site-packages/PySide6/Qt/lib/",
]
os.environ["LD_LIBRARY_PATH"] = ":".join(libraries)
block_cipher = None
DEBUGGING = True
EXCLUDE_BINARIES = True
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
        f'/app/airunner/src/airunner/main.py',
    ],
    pathex=[
        "/home/appuser/.local/lib/python3.10/site-packages/",
        "/home/appuser/.local/lib/python3.10/site-packages/torch/lib/",
        "/home/appuser/.local/lib/python3.10/site-packages/tokenizers/",
        "/home/appuser/.local/lib/python3.10/site-packages/tensorflow/",
        "/usr/lib/x86_64-linux-gnu/",
    ],
    binaries=[
        ('/home/appuser/.local/lib/python3.10/site-packages/nvidia/cudnn/lib/libcudnn_ops.so.9', '.'),
        ('/home/appuser/.local/lib/python3.10/site-packages/nvidia/cudnn/lib/libcudnn_cnn.so.9', '.'),
        ('/usr/lib/x86_64-linux-gnu/libgstgl-1.0.so.0', '.'),
        ("/usr/lib/x86_64-linux-gnu/libxcb-cursor.so.0", "."),
        ("/usr/lib/x86_64-linux-gnu/libxcb-cursor.so.0.0.0", "."),
        ("/usr/lib/x86_64-linux-gnu/libxcb-xinerama.so.0", "."),
        ("/usr/lib/x86_64-linux-gnu/libxcb-xinerama.so.0.0.0", "."),
        ("/usr/lib/x86_64-linux-gnu/libxcb-image.so.0", "."),
        ("/usr/lib/x86_64-linux-gnu/libxcb-image.so.0.0.0", "."),
        ("/usr/lib/x86_64-linux-gnu/libxcb-render-util.so.0.0.0", "."),
        ("/usr/lib/x86_64-linux-gnu/libxcb-render-util.so.0", "."),
        ("/usr/lib/x86_64-linux-gnu/libxcb-xkb.so.1", "."),
        ("/usr/lib/x86_64-linux-gnu/libxcb-xkb.so.1.0.0", "."),
    ],
    datas=datas,
    hiddenimports=[
        "airunner",
        "facehuggershield",
        "airunner.extensions",
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
        "opencv-python-headless",
        "PySide6",
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

import shutil
import os
import glob

# Define source directories
source_dirs = ['/app/airunner/src/airunner/widgets', '/app/airunner/src/airunner/windows']
destination_base_dir = '/app/dist/airunner'

# Copy all .ui files from source directories to the destination directory
for source_dir in source_dirs:
    for templates_dir in glob.glob(os.path.join(source_dir, '**', 'templates'), recursive=True):
        for ui_file in glob.glob(os.path.join(templates_dir, '*.ui'), recursive=True):
            # Create the corresponding subdirectory in the destination directory
            relative_path = os.path.relpath(ui_file, source_dir)
            destination_dir = os.path.join(destination_base_dir, os.path.dirname(relative_path))
            os.makedirs(destination_dir, exist_ok=True)
            # Copy the .ui file to the destination directory
            shutil.copy(ui_file, destination_dir)

os.makedirs('/app/dist/airunner/diffusers/pipelines/stable_diffusion', exist_ok=True)
os.makedirs('/app/dist/airunner/images', exist_ok=True)

# copy files for distribution
# shutil.copyfile('/app/linux.itch.toml', './dist/airunner/.itch.toml')
shutil.copyfile('/app/airunner/src/airunner/images/splashscreen.png', '/app/dist/airunner/images/splashscreen.png')
shutil.copytree('/app/airunner/src/airunner/styles/icons/dark/', '/app/dist/airunner/icons/dark/')
shutil.copytree('/app/airunner/src/airunner/styles/icons/light/', '/app/dist/airunner/icons/light/')

# copy alembic files
shutil.copytree('/app/airunner/src/airunner/alembic/', '/app/dist/airunner/_internal/alembic/')
shutil.copyfile('/app/airunner/src/airunner/alembic.ini', '/app/dist/airunner/_internal/alembic.ini')

# copy bootstrap data
shutil.copytree('/app/airunner/src/airunner/data/', '/app/dist/airunner/data/')

# copy llamaindex nltk cache requirements
shutil.copytree('/app/airunner/lib/corpora', '/app/dist/airunner/_internal/llama_index/core/_static/nltk_cache/corpora')
shutil.copytree('/app/airunner/lib/tokenizers', '/app/dist/airunner/_internal/llama_index/core/_static/nltk_cache/tokenizers')
