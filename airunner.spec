# -*- mode: python ; coding: utf-8 -*-
import os
import shutil
from PyInstaller.utils.hooks import copy_metadata, collect_data_files
import sys ; sys.setrecursionlimit(sys.getrecursionlimit() * 5)
os.environ["AIRUNNER_ENVIRONMENT"] = "prod"
libraries = [
    "./venv/lib/python3.10/site-packages/h5py.libs/",
    "./venv/lib/python3.10/site-packages/scipy.libs/",
    "./venv/lib/python3.10/site-packages/pillow.libs/",
    "./venv/lib/python3.10/site-packages/tokenizers/",
    "./opencv_python_headless.libs/",
    "./venv/lib/python3.10/site-packages/torchaudio/lib/",
    "./venv/lib/python3.10/site-packages/torch/lib/",
    "/usr/lib/python3.10",
    "/usr/lib/x86_64-linux-gnu/",
    "/usr/local/lib/",
    "/usr/local/lib/python3.10",
    "/usr/local/lib/python3.10/dist-packages",
    "./venv/lib/python3.10/site-packages/PySide6/Qt/plugins/platforms/",
    "./venv/lib/python3.10/site-packages/PySide6/Qt/lib/",
    "/usr/lib/x86_64-linux-gnu/qt6/plugins/platforms/",
    "./venv/lib/python3.10/site-packages/PySide6/Qt/plugins/platforms/",
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
datas = [
]
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
datas += copy_metadata('opencv-python-headless')
datas += collect_data_files("torch", include_py_files=True)
datas += collect_data_files("torchvision", include_py_files=True)
#datas += collect_data_files("JIT", include_py_files=True)
# datas += collect_data_files("pytorch_lightning", include_py_files=True)
# datas += collect_data_files("lightning_fabric", include_py_files=True)
datas += collect_data_files("transformers", include_py_files=True)
datas += collect_data_files("sympy", include_py_files=True)
datas += collect_data_files("controlnet_aux", include_py_files=True)
datas += collect_data_files("PySide6", include_py_files=True)
# datas += collect_data_files('PySide6', subdir='plugins/platforms')
#datas += [('/usr/lib/x86_64-linux-gnu/qt6/plugins/platforms', 'PySide6/plugins/platforms')]

a = Analysis(
    [
        f'./src/airunner/main.py',
    ],
    pathex=[
        "./venv/lib/python3.10/site-packages/",
        "./venv/lib/python3.10/site-packages/torch/lib",
        "./venv/lib/python3.10/site-packages/tokenizers",
        "./venv/lib/python3.10/site-packages/tensorflow",
        "/usr/lib/x86_64-linux-gnu/",
    ],
    binaries=[
        ('/usr/lib/x86_64-linux-gnu/libcudnn_ops_infer.so.8', '.'),
        ('/usr/lib/x86_64-linux-gnu/libcudnn_cnn_infer.so.8', '.'),
        # ('/usr/lib/x86_64-linux-gnu/qt6/plugins/platforms/libqxcb.so', '.'),
        # ('/usr/lib/x86_64-linux-gnu/libxcb-cursor.so', '.')
        ('./venv/lib/python3.10/site-packages/PySide6/Qt/plugins/platforms/clea.so', '.'),
        ('/usr/lib/x86_64-linux-gnu/libxcb-cursor.so', '.'),
        ('/usr/lib/x86_64-linux-gnu/libxcb-cursor.so.0', '.'),
        ('/usr/lib/x86_64-linux-gnu/libxcb-xinerama.so.0', '.'),
        ('/usr/lib/x86_64-linux-gnu/libxcb-xinput.so.0', '.'),
        ('/usr/lib/x86_64-linux-gnu/libxcb-icccm.so.4', '.'),
        ('/usr/lib/x86_64-linux-gnu/libxcb-image.so.0', '.'),
        ('/usr/lib/x86_64-linux-gnu/libxcb-keysyms.so.1', '.'),
        ('/usr/lib/x86_64-linux-gnu/libxcb-render-util.so.0', '.'),
        ('/usr/lib/x86_64-linux-gnu/libxcb-xkb.so.1', '.'),
    ],
    datas=datas,
    hiddenimports=[
        "xcb-cursor0",
        "airunner",
        #"JIT",
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
        # "omegaconf",
        "contextlib",
        "itertools",
        #"pytorch_lightning",
        "huggingface_hub.hf_api",
        "huggingface_hub.repository",
        "inspect",
        "psutil",
        "matplotlib",
        "numpy",
        "PIL._tkinter_finder",
        "sympy",
        "opencv-python-headless",
        "pytz",
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
source_dirs = ['./src/airunner/widgets', './src/airunner/windows']
destination_base_dir = './dist/airunner'

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



os.makedirs('./dist/airunner/diffusers/pipelines/stable_diffusion', exist_ok=True)
os.makedirs('./dist/airunner/images', exist_ok=True)

# copy files for distribution
# shutil.copyfile('./linux.itch.toml', './dist/airunner/.itch.toml')
shutil.copyfile('./src/airunner/images/splashscreen.png', './dist/airunner/images/splashscreen.png')
shutil.copytree('src/airunner/styles/icons/dark/', './dist/airunner/icons/dark/')
shutil.copytree('src/airunner/styles/icons/light/', './dist/airunner/icons/light/')

# copy alembic files
shutil.copytree('./src/airunner/alembic/', './dist/airunner/_internal/alembic/')
shutil.copyfile('./src/airunner/alembic.ini', './dist/airunner/_internal/alembic.ini')

# copy bootstrap data
shutil.copytree('./src/airunner/data/', './dist/airunner/data/')

# copy sd config files
# shutil.copyfile('./src/airunner/v1.yaml', './dist/airunner/v1.yaml')
# shutil.copyfile('./src/airunner/v2.yaml', './dist/airunner/v2.yaml')

# copy llamaindex nltk cache requirements
shutil.copytree('./lib/corpora', './dist/airunner/_internal/llama_index/core/_static/nltk_cache/corpora')
shutil.copytree('./lib/tokenizers', './dist/airunner/_internal/llama_index/core/_static/nltk_cache/tokenizers')

# shutil.copyfile(
#     f'./venv/lib/python3.10/site-packages/JIT/__pycache__/random.cpython-310.pyc',
#     f'./dist/airunner/random.pyc'
# )
