# -*- mode: python ; coding: utf-8 -*-
import os
import sys ; sys.setrecursionlimit(sys.getrecursionlimit() * 5)
import shutil
from PyInstaller.utils.hooks import copy_metadata, collect_data_files
os.environ["AIRUNNER_ENVIRONMENT"] = "prod"
os.environ["DEV_ENV"] = "0"
os.environ["PYTHONOPTIMIZE"] = "0"
block_cipher = None
ROOT = "Z:\\app\\airunner"
DIST = "./dist/airunner"
os.environ["AIRUNNER_ENVIRONMENT"] = "prod"
DEBUGGING = True
EXCLUDE_BINARIES = False
EXE_NAME = "airunner"  # used when creating a binary instead of a folder
EXE_STRIP = False
EXE_UPX = False
EXE_RUNTIME_TMP_DIR = None
COLLECT_NAME = 'airunner'
COLLECT_STRIP = False
COLLECT_UPX = False

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
datas += copy_metadata('sympy')
datas += copy_metadata('tensorflow')
datas += copy_metadata('scipy')
datas += collect_data_files("torch", include_py_files=True)
datas += collect_data_files("torchvision", include_py_files=True)
datas += collect_data_files("pytorch_lightning", include_py_files=True)
datas += collect_data_files("lightning_fabric", include_py_files=True)
datas += collect_data_files("transformers", include_py_files=True)
datas += collect_data_files("xformers", include_py_files=True)
datas += collect_data_files("tensorflow", include_py_files=True)
datas += collect_data_files("sympy", include_py_files=True)

a = Analysis(
    [
        f'{ROOT}\\src\\airunner\\main.py',
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
        #("C:\\Python310\\Lib\\site-packages\\torchvision\\cudart64_110.dll", "."),
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
        "aihandler",
        "airunner",
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
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "absl-py",
        "aiohttp",
        "aiosignal",
        "altgraph",
        "antlr4-python3-runtime",
        "anyio",
        "arrow",
        "async-timeout",
        "attrs",
        "beautifulsoup4",
        "blessed",
        "blinker",
        "cachetools",
        "charset-normalizer",
        "click",
        "cmake",
        "croniter",
        "cryptography",
        "dateutils",
        "dbus-python",
        "deepdiff",
        "distro",
        "distro-info",
        "dnspython",
        # "einops",
        "email-validator",
        "fastapi",
        "frozenlist",
        "google-auth",
        "google-auth-oauthlib",
        "google-pasta",
        "grpcio",
        "h11",
        "httpcore",
        # "httplib2",
        "httptools",
        "httpx",
        "importlib-metadata",
        "inquirer",
        "itsdangerous",
        "jax",
        "jeepney",
        "Jinja2",
        "keras",
        "keyring",
        "launchpadlib",
        "lazr.restfulclient",
        "lazr.uri",
        "libclang",
        "lightning-cloud",
        "lightning-utilities",
        "Markdown",
        "markdown-it-py",
        "MarkupSafe",
        "mdurl",
        "ml-dtypes",
        "more-itertools",
        "mpmath",
        "multidict",
        "mypy-extensions",
        "ninja",
        "nvidia-pyindex",
        "oauthlib",
        "opt-einsum",
        "ordered-set",
        "orjson",
        "psutil",
        "pyasn1",
        "pyasn1-modules",
        "pydantic",
        "Pygments",
        "PyGObject",
        "pyinstaller",
        "pyinstaller-hooks-contrib",
        "PyJWT",
        "pyparsing",
        "pyre-extensions",
        "python-apt",
        "python-dateutil",
        "python-dotenv",
        "python-editor",
        "python-multipart",
        "pytz",
        "PyYAML",
        "readchar",
        "rfc3986",
        "rsa",
        "SecretStorage",
        "sniffio",
        "soupsieve",
        "starlette",
        "starsessions",
        "sympy",
        "tensorboard",
        "tensorboard-data-server",
        "tensorboard-plugin-wit",
        "tensorflow-estimator",
        "tensorflow-io-gcs-filesystem",
        "torchaudio",
        "torchvision",
        "traitlets",
        "typing-inspect",
        "ujson",
        "unattended-upgrades",
        "uvicorn",
        "uvloop",
        "wadllib",
        "watchfiles",
        "wcwidth",
        "websocket-client",
        "websockets",
        "Werkzeug",
        "yarl",
        "zipp",
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
    onefile=False,
    onedir=True,
    upx_dir="C:\\Python310\\Scripts\\"
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
shutil.copyfile(
    f'{ROOT}/src/airunner/v1.yaml',
    f'{DIST}/v1.yaml'
)
shutil.copyfile(
    f'{ROOT}/src/airunner/v2.yaml',
    f'{DIST}/v2.yaml'
)