# -*- mode: python ; coding: utf-8 -*-

# This is a preliminary PyInstaller spec file for airunner.
# It includes common configurations for data files and hidden imports.
# Further testing and refinement will be needed.

import os
import glob

# Determine the project root directory, assuming the spec file is in the root
project_root = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(project_root, 'src')
airunner_pkg_dir = os.path.join(src_dir, 'airunner') # src/airunner
airunner_gui_dir = os.path.join(airunner_pkg_dir, 'gui') # src/airunner/gui
static_dir_root = os.path.join(project_root, 'static') # For project-level static assets


def collect_data_files_recursive(abs_search_base_dir, file_pattern, bundle_target_dir_prefix):
    """
    Collects files recursively and prepares them for PyInstaller's datas list.
    - abs_search_base_dir: Absolute path to the directory to start searching (e.g., project_root/src/airunner/gui/widgets).
    - file_pattern: Glob pattern for files (e.g., '*.ui').
    - bundle_target_dir_prefix: The directory path within the bundle where these files should be placed,
                                maintaining their subdirectory structure relative to abs_search_base_dir.
                                (e.g., 'airunner/gui/widgets')
    """
    collected_files = []
    # Ensure abs_search_base_dir exists to prevent glob errors if a directory is missing
    if not os.path.isdir(abs_search_base_dir):
        print(f"Warning: Source directory for data files not found: {abs_search_base_dir}")
        return collected_files

    for filepath in glob.glob(os.path.join(abs_search_base_dir, '**', file_pattern), recursive=True):
        if os.path.isfile(filepath): # Ensure it's a file, not a directory matched by glob somehow
            # Get the path of the file relative to the abs_search_base_dir
            # e.g., if abs_search_base_dir = /path/to/src/airunner/gui/widgets
            # and filepath = /path/to/src/airunner/gui/widgets/subdir/file.ui
            # then relative_path_in_source = subdir/file.ui
            relative_path_in_source = os.path.relpath(filepath, abs_search_base_dir)

            # Construct the destination path in the bundle
            # e.g., bundle_target_dir_prefix = airunner/gui/widgets
            # relative_path_in_source = subdir/file.ui
            # results in -> airunner/gui/widgets/subdir/file.ui
            # If relative_path_in_source is '.', it means the file is directly in abs_search_base_dir
            if relative_path_in_source == '.': # Should not happen with os.path.isfile and recursive glob on files
                destination_in_bundle = bundle_target_dir_prefix
            else:
                destination_in_bundle = os.path.join(bundle_target_dir_prefix, relative_path_in_source)
            
            collected_files.append((filepath, destination_in_bundle))
    return collected_files

# --- Data files ---
# These are files and directories that need to be bundled with the application.
# Format: list of tuples, where each tuple is (source_path, destination_in_bundle)

# 1. Data files from airunner package_data (relative to src/airunner/)
package_data_files = [
    (os.path.join(airunner_pkg_dir, 'alembic'), os.path.join('airunner', 'alembic')),
    (os.path.join(airunner_pkg_dir, 'cursors'), os.path.join('airunner', 'cursors')),
    (os.path.join(airunner_pkg_dir, 'filters'), os.path.join('airunner', 'filters')),
    (os.path.join(airunner_pkg_dir, 'icons'), os.path.join('airunner', 'icons')),
    (os.path.join(airunner_pkg_dir, 'images'), os.path.join('airunner', 'images')),
    (os.path.join(airunner_pkg_dir, 'styles'), os.path.join('airunner', 'styles')),
    # Removed broad directory copies for widgets and windows
    # (os.path.join(airunner_pkg_dir, 'widgets'), os.path.join('airunner', 'widgets')),
    # (os.path.join(airunner_pkg_dir, 'windows'), os.path.join('airunner', 'windows')),
    # Removed broad glob for QRC, will be handled by helper
    # (os.path.join(airunner_pkg_dir, '*.qrc'), os.path.join('airunner', '.')),
    (os.path.join(airunner_pkg_dir, '*.ini'), os.path.join('airunner', '.')), # Keep .ini as is, assumes they are at src/airunner/*.ini
]

# Add .ui files from gui/widgets and gui/windows
package_data_files.extend(collect_data_files_recursive(
    os.path.join(airunner_gui_dir, 'widgets'),
    '*.ui',
    os.path.join('airunner', 'gui', 'widgets')
))
package_data_files.extend(collect_data_files_recursive(
    os.path.join(airunner_gui_dir, 'windows'),
    '*.ui',
    os.path.join('airunner', 'gui', 'windows')
))

# Add .qrc files from src/airunner/ (assuming they are directly under src/airunner)
# If QRC files are in src/airunner/gui/resources, adjust base search path and bundle target path.
# Based on setup.py package_data: airunner: ["*.qrc"], they are at src/airunner/
package_data_files.extend(collect_data_files_recursive(
    airunner_pkg_dir, # Search in src/airunner/
    '*.qrc',
    'airunner' # Place them in airunner/ in the bundle
))


# 2. Static MathJax directory (relative to project root)
mathjax_data = [
    (os.path.join(static_dir_root, 'mathjax'), os.path.join('static', 'mathjax'))
]

# 3. Markdown documentation files (relative to project root, bundled at app root)
markdown_docs = [
    (os.path.join(project_root, 'WINDOWS_SETUP_GUIDE.md'), '.'),
    (os.path.join(project_root, 'TENSORRT_WINDOWS_SETUP.md'), '.'),
    (os.path.join(project_root, 'MECAB_WINDOWS_SETUP.md'), '.'),
]

all_datas = package_data_files + mathjax_data + markdown_docs

# --- Hidden Imports ---
# List of modules that PyInstaller might not detect automatically.
hidden_imports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtNetwork',
    'PySide6.QtSvg',
    'PySide6.QtPrintSupport',
    'torch',
    'transformers',
    'diffusers',
    'soundfile', # often a backend for audio libraries
    'sqlalchemy.dialects.sqlite',
    'alembic',
    'huggingface_hub',
    'llama_index.core',
    'llama_index.readers.file',
    # Add more llama_index submodules as identified, e.g.:
    'llama_index.llms.huggingface',
    'llama_index.llms.ollama',
    'llama_index.llms.openrouter',
    'llama_index.embeddings.huggingface',
    'llama_index.vector_stores.faiss',
    'sklearn', # scikit-learn and its submodules
    'sklearn.utils._typedefs', # Common sklearn hidden import
    'sklearn.neighbors._quad_tree', # Example of other sklearn hidden imports
    'scipy',
    'scipy.special',
    'scipy.linalg',
    'pandas', # If pandas is used, even transitively
    'numpy',
    'PIL', # Pillow, ensure all plugins are considered if specific image formats are problematic
    'pkg_resources.py2_warn',
    'sounddevice',
    'pyttsx3',
    'fugashi', # For Japanese MeCab support
    'mecab',   # The mecab-python3 package name
    'tensorrt',# For TensorRT support
    # Potentially problematic standard library modules if not picked up
    'importlib.metadata',
    'asyncio',
    'logging.handlers',
    'sqlite3',
    'shutil', # If used by any utility scripts or for data handling at runtime
    'pydantic.deprecated.class_validators', # For pydantic v2 if some libs still use old paths
    'pydantic.v1', # For pydantic v1 compatibility if needed by dependencies
    # Add any other known problematic imports for your specific dependencies here
    # e.g., 'torch.distributed', 'onnxruntime.capi.onnxruntime_GpuExecutionProvider' if using ORT with GPU
]


a = Analysis(
    ['src/airunner/main.py'],
    pathex=[project_root, src_dir], # Ensure both project root and src are available for imports
    binaries=[], # Placeholder for any non-Python .dll or .so files if needed
    datas=all_datas,
    hiddenimports=hidden_imports,
    hookspath=[], # Placeholder for custom PyInstaller hooks
    runtime_hooks=[], # Placeholder for runtime hooks
    excludes=[], # Modules to explicitly exclude
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None, # No encryption for the bytecode
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [], # Additional scripts to bundle
    exclude_binaries=True, # Exclude system binaries unless explicitly added to 'binaries'
    name='airunner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True, # UPX compression, if UPX is installed and desired
    upx_exclude=[],
    runtime_tmpdir=None, # Uses default temporary directory
    console=False, # Set to True for a console window (debugging), False for GUI app
    disable_windowed_traceback=False,
    target_arch=None, # Auto-detects architecture (e.g., 'x86_64')
    codesign_identity=None, # For macOS code signing
    entitlements_file=None, # For macOS entitlements
    # icon='path/to/your/icon.ico' # Specify icon path for Windows
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='airunner_dist', # Name of the output directory
)
