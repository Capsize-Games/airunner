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
datas += copy_metadata('aihandler')
datas += copy_metadata('tqdm')
datas += copy_metadata('regex')
datas += copy_metadata('requests')
datas += copy_metadata('packaging')
datas += copy_metadata('filelock')
datas += copy_metadata('numpy')
datas += copy_metadata('tokenizers')
datas += copy_metadata('transformers')
datas += copy_metadata('rich')
datas += collect_data_files("torch", include_py_files=True)
datas += collect_data_files("torchvision", include_py_files=True)
datas += collect_data_files("JIT", include_py_files=True)
datas += collect_data_files("triton", include_py_files=True)
datas += collect_data_files("pytorch_lightning", include_py_files=True)
datas += collect_data_files("lightning_fabric", include_py_files=True)
datas += collect_data_files("transformers", include_py_files=True)
datas += collect_data_files("xformers", include_py_files=True)
a = Analysis(
    [
        f'./airunner/src/airunner/main.py',
    ],
    pathex=[
        "/usr/local/lib/python3.10/dist-packages/",
        "/usr/local/lib/python3.10/dist-packages/torch/lib",
        "/usr/local/lib/python3.10/dist-packages/tokenizers",
        "/usr/local/lib/python3.10/dist-packages/tensorflow",
        "/usr/local/lib/python3.10/dist-packages/triton",
        "/usr/local/lib/python3.10/dist-packages/xformers",
        "/usr/local/lib/python3.10/dist-packages/xformers/triton",
        "/usr/lib/x86_64-linux-gnu/",
    ],
    binaries=[
        ('/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn_ops_infer.so.8', '.'),
        ('/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn_cnn_infer.so.8', '.'),
    ],
    datas=datas,
    hiddenimports=[
        "aihandler",
        "JIT",
        "triton",
        "triton._C",
        "triton._C.libtriton",
        "xformers",
        "xformers.ops",
        "xformers.triton",
        "xformers.triton.softmax",
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
        "bitsandbytes",
        "numpy",
        "PIL._tkinter_finder",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
shutil.copytree('./src/airunner/pyqt', './dist/airunner/pyqt')
shutil.copyfile('./linux.itch.toml', './dist/airunner/.itch.toml')
shutil.copytree('./src/airunner/src/icons', './dist/airunner/src/icons')

# copy sd config files
os.makedirs('./dist/airunner/diffusers/pipelines/stable_diffusion', exist_ok=True)
shutil.copyfile('./v1.yaml', './dist/airunner/v1.yaml')
shutil.copyfile('./v2.yaml', './dist/airunner/v2.yaml')

#############################################################
#### The following fixes are for Triton #####################

# run compileall on ./dist/airunner/triton/runtime/jit.py and then mv ./dist/airunner/triton/runtime/__pycache__/jit.cpython-310.pyc to ./dist/airunner/triton/runtime/jit.pyc
shutil.move(
    '/usr/local/lib/python3.10/dist-packages/triton/runtime/__pycache__/jit.cpython-310.pyc',
    './dist/airunner/triton/runtime/jit.pyc'
)

# do the same thing for ./dist/airunner/triton/compiler.py
shutil.move(
    '/usr/local/lib/python3.10/dist-packages/triton/__pycache__/compiler.cpython-310.pyc',
    './dist/airunner/triton/compiler.pyc'
)

for file in [ "random" ]:
    shutil.move(
        f'/usr/local/lib/python3.10/dist-packages/JIT/__pycache__/{file}.cpython-310.pyc',
        f'./dist/airunner/{file}.pyc'
    )