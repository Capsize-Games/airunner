# -*- mode: python ; coding: utf-8 -*-
import site
import shutil
import os
import glob
from os.path import join
# Import PyInstaller hook utilities
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

base_path = "/app"
# Correct the site-packages path for the CI environment
site_packages_path = "/home/appuser/.local/share/airunner/python/lib/python3.10/site-packages"
dist = join(base_path, "dist")
airunner_path = join(base_path, "src/airunner")
cudnn_lib = join(site_packages_path, 'nvidia/cudnn/lib')
pyside_lib = join(site_packages_path, 'PySide6/Qt/lib')
linux_lib = '/usr/lib/x86_64-linux-gnu'
nss_lib = linux_lib  # NSS libraries location
gtk_lib = linux_lib  # GTK libraries location
db_lib = linux_lib   # Database libraries location

# Update CUDA paths for CUDA 12.x which supports 50xx GPUs
cuda_lib = '/usr/local/cuda/lib64'  # Updated path for CUDA 12.x
torch_lib = join(site_packages_path, 'torch/lib')  # PyTorch's bundled CUDA libraries

qt_lib = join(site_packages_path, 'PySide6/Qt/lib/')
python_include_path = "/usr/include/python3.10"

# Get all necessary PyTorch bundled CUDA libraries
torch_cuda_libs = []
for lib_pattern in [
    # JIT link libraries (critical for RTX 5080)
    "libnvJitLink*.so*",
    # Core CUDA libraries from PyTorch
    "libcuda*.so*", 
    "libcublas*.so*", 
    "libcudnn*.so*", 
    "libcufft*.so*",
    "libcurand*.so*",
    "libcusparse*.so*",
    "libcusolver*.so*",
    "libnvToolsExt*.so*",
    "libnvrtc*.so*",
]:
    for cuda_so in glob.glob(join(torch_lib, lib_pattern)):
        if os.path.isfile(cuda_so) and not os.path.islink(cuda_so):
            torch_cuda_libs.append((cuda_so, '.'))

# Get PyTorch's NVIDIA libraries 
for nvidia_dir in ['cusparse', 'cublas', 'cudnn', 'cufft', 'curand', 'cusolver']:
    nvidia_path = join(site_packages_path, f'nvidia/{nvidia_dir}/lib')
    if os.path.exists(nvidia_path):
        for lib_file in glob.glob(join(nvidia_path, f'lib{nvidia_dir}*.so*')):
            if os.path.isfile(lib_file) and not os.path.islink(lib_file):
                torch_cuda_libs.append((lib_file, f'nvidia/{nvidia_dir}/lib'))

# Get key system CUDA libraries (if needed)
system_cuda_libs = []
for cuda_so in glob.glob(join(cuda_lib, "*.so*")):
    if os.path.isfile(cuda_so) and not os.path.islink(cuda_so) and 'stubs' not in cuda_so:
        system_cuda_libs.append((cuda_so, '.'))

a = Analysis(
    [join(airunner_path, 'main.py')],
    pathex=[
        join(base_path, 'src'),
    ],
    binaries=[
        # ...existing binaries...
        (join(site_packages_path, 'tiktoken/_tiktoken.cpython-310-x86_64-linux-gnu.so'), 'tiktoken'),
        
        # Add PyTorch's CUDA libraries first (prioritize these)
        *torch_cuda_libs,
        
        # Add system CUDA libraries as fallback
        *system_cuda_libs,
        
        # QT libraries
        (join(qt_lib, 'libQt6XcbQpa.so.6'), '.'),
        (join(qt_lib, 'libQt6DBus.so.6'), '.'),
        (join(qt_lib, 'libQt6Widgets.so.6'), '.'),
        (join(qt_lib, 'libQt6Gui.so.6'), '.'),
        (join(qt_lib, 'libQt6Core.so.6'), '.'),
        (join(linux_lib, 'libpython3.10.so.1.0'), '.'),
        (join(linux_lib, 'libxcb.so.1.1.0'), '.'),
        (join(linux_lib, 'libxkbcommon-x11.so.0.0.0'), '.'),
        
        # ...existing system libraries...
        # NSS libraries for QtWebEngine
        (join(nss_lib, 'libplds4.so'), '.'),
        (join(nss_lib, 'libplc4.so'), '.'),
        (join(nss_lib, 'libnss3.so'), '.'),
        (join(nss_lib, 'libnssutil3.so'), '.'),
        (join(nss_lib, 'libnspr4.so'), '.'),
        (join(nss_lib, 'libsmime3.so'), '.'),
        # GTK libraries
        (join(gtk_lib, 'libatk-1.0.so.0'), '.'),
        (join(gtk_lib, 'libgtk-3.so.0'), '.'),
        (join(gtk_lib, 'libgdk-3.so.0'), '.'),
        # Database libraries
        (join(db_lib, 'libpq.so.5'), '.'),
        (join(db_lib, 'libodbc.so.2'), '.'),
        (join(db_lib, 'libmysqlclient.so.21'), '.'),
        # Other system libraries
        (join(linux_lib, 'libpcsclite.so'), '.'),
        (join(linux_lib, 'libpcsclite.so.1'), '.'),
        (join(linux_lib, 'libcups.so'), '.'),
        (join(linux_lib, 'libcups.so.2'), '.'),
        (join(linux_lib, 'libspeechd.so'), '.'),
        (join(linux_lib, 'libspeechd.so.2'), '.'),
        (join(linux_lib, 'libspeechd.so.2.6.0'), '.'),
        (join(linux_lib, 'libsox.so'), '.'),
        (join(linux_lib, 'libsox.so.3'), '.'),
        (join(linux_lib, 'libsox.so.3.0.0'), '.'),
        (join(linux_lib, 'libtbb.so'), '.'),
        (join(linux_lib, 'libtbb.so.2'), '.'),
        (join(linux_lib, 'libtbb.so.12.5'), '.'),
        (join(linux_lib, 'libtbb.so.12'), '.'),
        (portaudio_path, '.'),
    ],
    datas=[
        (join(airunner_path, 'alembic.ini'), 'airunner'),
        (python_include_path, 'include/python3.10'),
        (join(site_packages_path, 'inflect'), 'inflect'),
        (join(site_packages_path, 'controlnet_aux'), 'controlnet_aux'),
        (join(site_packages_path, 'tiktoken'), 'tiktoken'),
        (join(site_packages_path, 'tiktoken_ext'), 'tiktoken_ext'),
        (join(site_packages_path, 'pydantic'), 'pydantic'),
        (join(site_packages_path, 'nvidia'), 'nvidia'),
        (join(site_packages_path, 'llama_index'), 'llama_index'),
        (join(site_packages_path, 'PySide6'), 'PySide6'),
        (join(site_packages_path, 'PySide6/Qt/plugins/platforms'), 'platforms'),
        # Use collect_data_files to gather triton source and data files
        *collect_data_files('triton', include_py_files=True),
        *collect_data_files('torchao', include_py_files=True), # Add torchao sources
        (join(airunner_path, 'alembic'), 'airunner/alembic'),
        (join(airunner_path, 'alembic.ini'), '.'),
        *copy_metadata('safetensors'), # Keep safetensors metadata
        *collect_data_files('safetensors', include_py_files=True) # Keep safetensors data
    ],
    hiddenimports=[
        'airunner',
        'airunner.data.models',
        'airunner.utils',
        'airunner.utils.db',
        'airunner.utils.db.bootstrap',
        'airunner.utils.db.column',
        'airunner.utils.db.engine',
        'airunner.utils.db.table',
        'airunner.utils.image',
        'airunner.data.bootstrap.controlnet_bootstrap_data',
        'airunner.data.bootstrap.font_settings_bootstrap_data',
        'airunner.data.bootstrap.imagefilter_bootstrap_data',
        'airunner.data.bootstrap.model_bootstrap_data',
        'airunner.data.bootstrap.pipeline_bootstrap_data',
        'airunner.data.bootstrap.prompt_templates_bootstrap_data',
        
        'diffusers',
        # safetensors handling (remains in spec)
        'safetensors',
        *collect_submodules('safetensors'),

        'huggingface_hub.utils',
        'torch',
        'torch.jit',
        'torch.jit._script',
        'torch.jit.frontend',
        'torch._sources',
        'tiktoken',
        'tiktoken.model',
        'tiktoken.registry',
        'tiktoken_ext',
        'nvidia',
        'nvidia.lib',
        'nvidia.lib.cudnn',
        'llama_index',
        'llama_index.core',
        'llama_index.readers',
        'llama_index.readers.file',
        'llama_index.core.node_parser',
        'llama_index.core.chat_engine',
        'llama_index.core.indices.keyword_table',
        'llama_index.core.base.llms.types',
        'logging',
        'logging.config',
        'PySide6',
        'scipy.special._cdflib',
        'pysqlite2',
        'triton',
        'triton.runtime',
        'triton.runtime.driver',
        'triton.backends',
        'triton.backends.nvidia',
        'torchao',
        'torchao.kernel',
        'torchao.quantization',
    ],
    hookspath=['/app/package/pyinstaller/hooks'], # Use custom hooks
    hooksconfig={},
    runtime_hooks=[
        '/app/package/pyinstaller/hooks/runtime-hook-cuda-50xx.py'  # Add our 50xx-specific CUDA runtime hook
    ],
    excludes=[
        'tensorflow',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='airunner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # onefile=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='airunner',
)

# Copy files to dist paths
internal_path = join(base_path, dist, "airunner/_internal")

images_path = join(airunner_path, 'gui/images/')
images_path_out = join(internal_path, "airunner/gui/images")
print(f"Copy images from {images_path} to {images_path_out}")
shutil.copytree(images_path, images_path_out)

styles_path = join(airunner_path, 'gui/styles/')
styles_path_out = join(internal_path, "airunner/gui/styles")
print(f"Copy styles from {styles_path} to {styles_path_out}")
shutil.copytree(styles_path, styles_path_out)

alembic_path = join(airunner_path, 'alembic/')
alembic_path_out = join(internal_path, "alembic")
print(f"Copy alembic from {alembic_path} to {alembic_path_out}")
shutil.copytree(alembic_path, alembic_path_out)

data_path = join(airunner_path, 'data/')
data_path_out = join(base_path, dist, "airunner/_internal/airunner/data")
print(f"Copy data from {data_path} to {data_path_out}")
shutil.copytree(data_path, data_path_out)

punkt_path = '/home/appuser/nltk_data/tokenizers/punkt'
punkt_path_out = join(internal_path, "llama_index/core/_static/nltk_cache/tokenizers/punkt")
print(f"Copy punkt from {punkt_path} to {punkt_path_out}")
shutil.copytree(punkt_path, punkt_path_out)

# Create a marker file to indicate this is an RTX 50xx build
marker_file_path = os.path.join(os.path.dirname(SPECPATH), '..', 'dist', 'airunner', '_internal', 'rtx50xx_build')
os.makedirs(os.path.dirname(marker_file_path), exist_ok=True)
with open(marker_file_path, 'w') as f:
    f.write('This is an RTX 50xx-specific build\n')