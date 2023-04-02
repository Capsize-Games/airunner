# -*- mode: python ; coding: utf-8 -*-
import os
import sys ; sys.setrecursionlimit(sys.getrecursionlimit() * 5)
import shutil
from PyInstaller.utils.hooks import copy_metadata, collect_data_files
os.environ["AIRUNNER_ENVIRONMENT"] = "prod"
block_cipher = None
DEBUGGING = False
ONE_fILE = False
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
# datas += collect_data_files("JIT", include_py_files=True)
datas += collect_data_files("pytorch_lightning", include_py_files=True)
datas += collect_data_files("lightning_fabric", include_py_files=True)
datas += collect_data_files("transformers", include_py_files=True)
datas += collect_data_files("xformers", include_py_files=True)
#datas += collect_data_files("deepspeed", include_py_files=True)
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
        "C:\\Python310\\Lib\\site-packages",
        "C:\\Python310\\Lib\\site-packages\\tokenizers",
        "C:\\Python310\\Lib\\site-packages\\PyQt6",
        "C:\\Python310\\Lib\\site-packages\\tensorflow_io_gcs_filesystem\\core\\python\\ops",
        "C:\\Python310\\Lib\\site-packages\\bitsandbytes\\",
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
    ],
    datas=datas,
    hiddenimports=[
        # "JIT",
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
        # "pyqt6",
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

if ONE_fILE:
    splash = Splash('../airunner/src/airunner/src/splashscreen.png',
      binaries=a.binaries,
      datas=a.datas,
      text_pos=(10, 50),
      text_size=12,
      text_color='black',
      text_font='Arial',
      text='Loading...',
    )
    binaries = splash.binaries

    binaries.append(
        ("cudart64_110.dll", "C:\\Python310\\Lib\\site-packages\\torchvision\\cudart64_110.dll", "BINARY")
    )
    binaries.append(
        ("vcruntime140.dll", "C:\\Python310\\vcruntime140.dll", "BINARY")
    )

    exe = EXE(pyz,
      a.scripts,
      splash,
      a.binaries,
      a.zipfiles,
      a.datas,
      name='airunner',
      debug=DEBUGGING,
      strip=False,
      upx=True,
      runtime_tmpdir=None,
      console=DEBUGGING
    )

    shutil.copytree(
        f"{ROOT}airunner\\src\\airunner\\pyqt",
        f'{DIST}/pyqt'
    )
    shutil.copytree(
        f"{ROOT}airunner\\src\\",
        f'{DIST}/src'
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='airunner',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=True,
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
        strip=False,
        upx=False,
        upx_exclude=[],
        name='airunner',
    )

    shutil.copytree(
        f'{ROOT}/airunner/src/airunner/pyqt',
        f'{DIST}/pyqt'
    )
    shutil.copyfile(
        f'{ROOT}/manifests/airunner_gui/windows.itch.toml',
        f'{DIST}/.itch.toml'
    )
    shutil.copytree(
        f'{ROOT}/airunner/src/airunner/src/icons',
        f'{DIST}/src/icons'
    )