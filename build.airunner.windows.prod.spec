# -*- mode: python ; coding: utf-8 -*-
import os
import sys ; sys.setrecursionlimit(sys.getrecursionlimit() * 5)
import shutil
from PyInstaller.utils.hooks import copy_metadata, collect_data_files
os.environ["AIRUNNER_ENVIRONMENT"] = "prod"
os.environ["DEV_ENV"] = "0"
os.environ["PYTHONOPTIMIZE"] = "0"
block_cipher = None
ROOT = "Z:\\app\\"
DIST = "./dist/airunner"

os.environ["PYTHONOPTIMIZE"] = "0"
os.environ["LD_LIBRARY_PATH"] = "C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v11.7\\bin"
os.environ["PATH"] = f"{os.environ['PATH']};C:\\"
os.environ["PATH"] = f"{os.environ['PATH']};C:\\Users\\mainr\\AppData\\Local\\Programs\\Python\\Python310"
os.environ["PATH"] = f"{os.environ['PATH']};C:\\Users\\mainr\\PycharmProjects\\runaiux\\venv\\Lib\\site-packages"
os.environ["PATH"] = f"{os.environ['PATH']};C:\\Users\\mainr\\PycharmProjects\\runaiux\\venv\\Lib\\site-packages\\lib"
os.environ["PATH"] = f"{os.environ['PATH']};C:\\Program Files\\NVIDIA\CUDNN\\8.6.0.163\\lib"
os.environ["PATH"] = f"{os.environ['PATH']};C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v11.7\\bin"
os.environ.setdefault("PYTHONPATH", "C:\\Users\\mainr\\PycharmProjects\\runaiux\\venv\\Lib\\site-packages")
os.environ["PYTHONPATH"] = f"{os.environ['PYTHONPATH']};C:\\"
os.environ["PYTHONPATH"] = f"{os.environ['PYTHONPATH']};C:\\Users\\mainr\\AppData\\Local\\Programs\\Python\\Python310"
os.environ["PYTHONPATH"] = f"{os.environ['PYTHONPATH']};C:\\PortableGit"
os.environ["PYTHONPATH"] = f"{os.environ['PYTHONPATH']};C:\\Program Files\\NVIDIA\\CUDNN\\v8.6.0.163\\bin"
os.environ["PYTHONPATH"] = f"{os.environ['PYTHONPATH']};C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v11.7\\bin"
os.environ["PYTHONPATH"] = f"{os.environ['PYTHONPATH']};C:\\Users\\mainr\\PycharmProjects\\runaiux\\venv\\Lib\\site-packages\\torch\\lib"
os.environ["LD_LIBRARY_PATH"] = f"{os.environ['PATH']};{os.environ['PYTHONPATH']};{os.environ['LD_LIBRARY_PATH']}"
os.environ["DISABLE_TELEMETRY"] = f"true"
os.environ["HF_ENDPOINT"] = f""
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = f"0"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = f"1"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = f"0"
os.environ["USE_SAFETENSORS"] = f"true"
os.environ["NVIDIA_VISIBLE_DEVICES"] = f"true"
os.environ["XFORMERS_MORE_DETAILS"] = f"1"

DEBUGGING = False
EXCLUDE_BINARIES = False
EXE_NAME = "airunner"  # used when creating a binary instead of a folder
EXE_STRIP = False
EXE_UPX = True
EXE_RUNTIME_TMP_DIR = None
COLLECT_NAME = 'airunner'
COLLECT_STRIP = False
COLLECT_UPX = True

datas = []
datas += copy_metadata('aihandlerwindows')
datas += copy_metadata('tqdm')
datas += copy_metadata('regex')
datas += copy_metadata('requests')
datas += copy_metadata('packaging')
datas += copy_metadata('filelock')
datas += copy_metadata('numpy')
datas += copy_metadata('tokenizers')
datas += copy_metadata('transformers')
datas += copy_metadata('rich')
datas += copy_metadata('tensorflow')
datas += copy_metadata('scipy')
datas += collect_data_files("torch", include_py_files=True)
datas += collect_data_files("torchvision", include_py_files=True)
datas += collect_data_files("pytorch_lightning", include_py_files=True)
datas += collect_data_files("lightning_fabric", include_py_files=True)
datas += collect_data_files("transformers", include_py_files=True)
datas += collect_data_files("xformers", include_py_files=True)
datas += collect_data_files("tensorflow", include_py_files=True)

a = Analysis(
    [
        f'{ROOT}airunner\\src\\airunner\\main.py',
    ],
    pathex=[
        "C:\\Python310\\Lib\\site-packages",
        "C:\\Python310\\Lib\\site-packages\\tokenizers",
        "C:\\Python310\\Lib\\site-packages\\tensorflow_io_gcs_filesystem\\core\\python\\ops",
        "C:\\Python310\\Lib\\site-packages\\bitsandbytes\\",
        "C:\\Python310\\Lib\\site-packages\\tensorflow\\python\\data\\experimental\\service\\",
        "C:\\Python310\\Lib\\site-packages\\torch\\lib",
        "C:\\Python310\\Lib\\site-packages\\PyQt6",
        "C:\\Users\\root\\AppData\\Local\\Programs\\Python\\Python310\\Lib\\site-packages\\tensorflow\\python\\data\\experimental\\service\\",
        "C:\\Python310\\Lib\\site-packages\\xformers\\",
        "C:\\Users\\root\\AppData\\Local\\Programs\\Python\\Python310\\",
    ],
    binaries=[
        ("C:\\Python310\\Lib\\site-packages\\torchvision\\cudart64_110.dll", "."),
        ("C:\\Python310\\tcl\\tk8.6\\demos\\text.tcl", "."),
        ("C:\\Python310\\tcl\\tk8.6\\ttk\\fonts.tcl", "."),
        ("C:\\Python310\\tcl\\tk8.6\\ttk\\utils.tcl", "."),
        ("C:\\Python310\\tcl\\tk8.6\\ttk\\cursors.tcl", "."),
        ("C:\\Python310\\DLLs\\tcl86t.dll", "."),
        ("C:\\Python310\\DLLs\\tk86t.dll", "."),
        ("C:\\Python310\\vcruntime140.dll", "."),
        ("C:\\Python310\\vcruntime140_1.dll", "."),
        ("C:\\Python310\\tcl\\tcl8.6\\tzdata", "."),
        ("C:\\windows\\syswow64\\msvcp140.dll", "."),
        ("C:\\api-ms-win-shcore-scaling-l1-1-1.dll", "."),
        ("C:\\Python310\\Lib\\site-packages\\tensorflow\\python\\util\\_pywrap_utils.pyd", "."),
    ],
    datas=datas,
    hiddenimports=[
        "accelerate",
        "xformers",
        "xformers.ops",
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
        "bitsandbytes",
        "PIL._tkinter_finder",
        "scipy",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "tensorboard",
        "torchaudio",
        "markupsafe",
        "google",
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
    bootloader_ignore_signals=False,
    strip=EXE_STRIP,
    upx=EXE_UPX,
    console=DEBUGGING,
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
    upx=COLLECT_UPX,
    upx_exclude=[],
    name=COLLECT_NAME,
)

shutil.copytree(
    f'{ROOT}/airunner/src/airunner/pyqt',
    f'{DIST}/pyqt'
)
shutil.copyfile(
    f'{ROOT}/windows.itch.toml',
    f'{DIST}/.itch.toml'
)
shutil.copytree(
    f'{ROOT}/airunner/src/airunner/src/icons',
    f'{DIST}/src/icons'
)