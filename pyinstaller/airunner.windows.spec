# -*- mode: python ; coding: utf-8 -*-

# This spec file is designed to be run inside a Wine environment (e.g., via Docker)
# Paths should reflect the Wine file system structure (e.g., C:\Python310, Z:\app if mounted)

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

# Assuming the project root is mounted to /app in Docker, which maps to Z:\app in Wine
# Or if files are copied to C:\app within the Docker build process
# Adjust base_path if your container setup differs.
# PyInstaller runs from the directory containing the spec file.
# We need to point to the source directory relative to the spec file location.
src_path = os.path.abspath(os.path.join(SPECPATH, '..', 'src'))
# PyInstaller needs paths in the host (Linux) format for analysis,
# but collected files will be placed correctly for Windows.
pathex = [src_path]

# --- Data Files ---
# Collect data files from the airunner package relative to src_path
# PyInstaller hooks often handle common packages like PySide6, but explicit collection might be needed.
datas = []
datas += collect_data_files('airunner', include_py_files=False, subdir='.', datas_dst='airunner')
datas += collect_data_files('llama_index', datas_dst='llama_index')
datas += collect_data_files('tiktoken', datas_dst='tiktoken')
datas += collect_data_files('huggingface_hub', datas_dst='huggingface_hub')
datas += collect_data_files('diffusers', datas_dst='diffusers')
datas += collect_data_files('transformers', datas_dst='transformers')
datas += collect_data_files('sqlalchemy', datas_dst='sqlalchemy')
datas += collect_data_files('alembic', datas_dst='alembic')
datas += collect_data_files('pydantic', datas_dst='pydantic')
datas += collect_data_files('PySide6', datas_dst='PySide6') # Ensure Qt plugins etc. are included

# Add specific non-code files if not automatically included
# Adjust source paths relative to the project root (SPECPATH/..)
datas += [
    (os.path.join(src_path, 'airunner', 'alembic.ini'), 'airunner'),
    (os.path.join(src_path, 'airunner', 'alembic'), 'airunner/alembic'),
    # Add other necessary assets like icons, images, styles, UI files
    (os.path.join(src_path, 'airunner', 'gui', 'images'), 'airunner/gui/images'),
    (os.path.join(src_path, 'airunner', 'gui', 'styles'), 'airunner/gui/styles'),
    # Add NLTK data if needed, assuming it's downloaded to a known location
    # Example: (os.path.join(SPECPATH, '..', 'lib', 'tokenizers', 'punkt'), 'nltk_data/tokenizers/punkt'),
    # Example: (os.path.join(SPECPATH, '..', 'lib', 'corpora', 'stopwords'), 'nltk_data/corpora/stopwords'),
]

# --- Hidden Imports ---
# List modules that PyInstaller might miss
hiddenimports = []
hiddenimports += collect_submodules('airunner')
hiddenimports += collect_submodules('PySide6')
hiddenimports += collect_submodules('sqlalchemy')
hiddenimports += collect_submodules('huggingface_hub')
hiddenimports += collect_submodules('transformers')
hiddenimports += collect_submodules('diffusers')
hiddenimports += collect_submodules('llama_index')
hiddenimports += collect_submodules('tiktoken')
hiddenimports += collect_submodules('alembic')
hiddenimports += collect_submodules('pydantic')
hiddenimports += ['pkg_resources.py2_warn']
hiddenimports += ['scipy.special._cdflib'] # Common hidden import for scipy
# Add others based on runtime errors or known dependencies
hiddenimports += ['logging.config']

# --- Binaries ---
# PyInstaller usually handles DLLs well on Windows. Add specific DLLs
# only if they are missed. Paths should be valid within the Wine environment.
# Example: binaries = [ ('C:\path\to\your.dll', '.') ]
binaries = []
# Note: Packaging CUDA/cuDNN for Windows via PyInstaller is complex and often requires
# manual copying of DLLs and setting environment variables. This spec assumes CPU execution.

a = Analysis(
    [os.path.join(src_path, 'airunner', 'main.py')],
    pathex=pathex,
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', # Exclude Tkinter if not used
        'fix_qt_pkg_config', # Linux specific hook
        # Add other modules to exclude if known not needed for Windows
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False, # Set to True if using manifest files
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='airunner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True, # UPX compression can sometimes cause issues, set to False if needed
    console=False, # Set to False for a GUI application (no console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None, # None defaults to the Wine architecture (win64)
    codesign_identity=None,
    entitlements_file=None,
    # Ensure the icon path is correct relative to the spec file
    icon=os.path.join(src_path, 'airunner', 'gui', 'images', 'airunner.ico') # Assuming icon exists here
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles, # Include PYZ file
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='airunner_windows', # Name of the output folder in dist/
)

# Post-build steps (like copying NLTK data if not handled by datas)
# can be added here using Python's os and shutil, but ensure paths
# work within the context where PyInstaller runs the spec file.
# Example:
# import shutil
# nltk_data_src = os.path.join(SPECPATH, '..', 'lib') # Adjust source
# nltk_data_dest = os.path.join(DISTPATH, 'airunner_windows', 'nltk_data')
# if os.path.exists(nltk_data_src):
#     shutil.copytree(os.path.join(nltk_data_src, 'tokenizers'), os.path.join(nltk_data_dest, 'tokenizers'), dirs_exist_ok=True)
#     shutil.copytree(os.path.join(nltk_data_src, 'corpora'), os.path.join(nltk_data_dest, 'corpora'), dirs_exist_ok=True)

