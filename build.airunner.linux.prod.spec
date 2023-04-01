# -*- mode: python ; coding: utf-8 -*-
import os
import shutil
from PyInstaller.utils.hooks import copy_metadata, collect_data_files
import sys ; sys.setrecursionlimit(sys.getrecursionlimit() * 5)
os.environ["AIRUNNER_ENVIRONMENT"] = "prod"
block_cipher = None
DEBUGGING = False
ONE_fILE = False
ROOT = "/app"
DIST = "./dist/airunner"
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
datas += collect_data_files("deepspeed", include_py_files=True)

a = Analysis(
    [
        f'{ROOT}/src/airunner/main.py',
    ],
    pathex=[
        f"{ROOT}/src/airunner/pyqt/",
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
        ('/usr/lib/x86_64-linux-gnu/libpython3.10.so.1.0', '.'),
        ('/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn_ops_infer.so.8', '.'),
        ('/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn_cnn_infer.so.8', '.'),
        ('/usr/lib/x86_64-linux-gnu/libtcl8.6.so', '.')
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
        "taming",
        "taming.modules",
        "taming.modules.vqvae",
        "taming.modules.vqvae.quantize",
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

if ONE_fILE:
    splash = Splash(f'{ROOT}/src/airunner/src/splashscreen.png',
      binaries=a.binaries,
      datas=a.datas,
      text_pos=(10, 50),
      text_size=12,
      text_color='black',
      text_font='Arial',
      text='Loading...',
    )
    exe = EXE(pyz,
      a.scripts,
      splash,
      splash.binaries,
      a.zipfiles,
      a.datas,
      name='airunner',
      debug=DEBUGGING,
      strip=False,
      upx=True,
      runtime_tmpdir=None,
      console=DEBUGGING
    )
else:
    exe = EXE(
      pyz,
      a.scripts,
      [],
      exclude_binaries=True,
      name='airunner',
      debug=DEBUGGING,
      strip=False,
      upx=True,
      runtime_tmpdir=None,
      console=DEBUGGING
    )
    coll = COLLECT(
      exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='airunner'
    )

    shutil.copytree(
        f'{ROOT}/src/airunner/pyqt',
        f'{DIST}/pyqt'
    )

    shutil.copyfile(
        f'{ROOT}/linux.itch.toml',
        f'{DIST}/.itch.toml'
    )

    shutil.copytree(
        f'{ROOT}/src/airunner/src/icons',
        f'{DIST}/src/icons'
    )

    for file in ["v1.yaml", "v2.yaml"]:
        # create f'{DIST}/diffusers/pipelines/stable_diffusion' if it doesn't exist
        os.makedirs(f'{DIST}/diffusers/pipelines/stable_diffusion', exist_ok=True)
        shutil.copyfile(
            f'{ROOT}/{file}',
            f'{DIST}/diffusers/pipelines/stable_diffusion/{file}'
        )