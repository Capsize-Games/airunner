# -*- mode: python ; coding: utf-8 -*-
import os
import shutil
from PyInstaller.utils.hooks import copy_metadata, collect_data_files
import sys ; sys.setrecursionlimit(sys.getrecursionlimit() * 5)
os.environ["AIRUNNER_ENVIRONMENT"] = "prod"
libraries = [
    "/usr/local/lib/python3.10/dist-packages/PyQt6/Qt6/lib/",
    "/usr/lib/x86_64-linux-gnu/wine-development/",
    "/usr/local/lib/python3.10/dist-packages/h5py.libs/",
    "/usr/local/lib/python3.10/dist-packages/scipy.libs/",
    "/usr/local/lib/python3.10/dist-packages/tokenizers.libs/",
    "/usr/local/lib/python3.10/dist-packages/Pillow.libs/",
    "/usr/local/lib/python3.10/dist-packages/opencv_python.libs/",
    "/usr/local/lib/python3.10/dist-packages/torchaudio/lib/",
    "/usr/local/lib/python3.10/dist-packages/torch/lib/",
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
        "/usr/local/lib/python3.10/dist-packages/",
        "/usr/local/lib/python3.10/dist-packages/torch/lib",
        "/usr/local/lib/python3.10/dist-packages/tokenizers",
        "/usr/lib/x86_64-linux-gnu/",
    ],
    binaries=[
        ('/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn_ops_infer.so.8', '.'),
        ('/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn_cnn_infer.so.8', '.'),
        ('/usr/lib/x86_64-linux-gnu/libgstgl-1.0.so.0', '.'),
    ],
    datas=datas,
    hiddenimports=[
        "airunner",
        "airunner.extensions",
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
shutil.copytree('/app/airunner/src/airunner/pyqt', '/app/dist/airunner/pyqt')
shutil.copyfile('/app/airunner/linux.itch.toml', '/app/dist/airunner/.itch.toml')
shutil.copytree('/app/airunner/src/airunner/src/icons', '/app/dist/airunner/src/icons')
shutil.copytree('/app/airunner/src/airunner/data', '/app/dist/airunner/data')
shutil.copyfile('/app/airunner/src/airunner/src/icon_256.png', '/app/dist/airunner/src/icon_256.png')
shutil.copyfile('/app/airunner/src/airunner/images/splashscreen.png', '/app/dist/airunner/images/splashscreen.png')

# copy sd config files
os.makedirs('/dist/airunner/diffusers/pipelines/stable_diffusion', exist_ok=True)
shutil.copyfile('/app/airunner/src/airunner/v1.yaml', '/app/dist/airunner/v1.yaml')
shutil.copyfile('/app/airunner/src/airunner/v2.yaml', '/app/dist/airunner/v2.yaml')
shutil.copyfile('/app/airunner/src/airunner/sd_xl_base.yaml', '/app/dist/airunner/sd_xl_base.yaml')
shutil.copyfile('/app/airunner/src/airunner/sd_xl_refiner.yaml', '/app/dist/airunner/sd_xl_refiner.yaml')

shutil.copyfile(
    f'/usr/local/lib/python3.10/dist-packages/JIT/__pycache__/random.cpython-310.pyc',
    f'/app/dist/airunner/random.pyc'
)
