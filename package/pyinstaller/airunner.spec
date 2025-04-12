# -*- mode: python ; coding: utf-8 -*-
import site
import shutil
import os
from os.path import join

base_path = "/app"
site_packages_path = "/home/appuser/.local/share/airunner/python/local/lib/python3.10/dist-packages/"
dist = join(base_path, "dist")
airunner_path = join(base_path, "src/airunner")
cudnn_lib = join(site_packages_path, 'nvidia/cudnn/lib')
pyside_lib = join(site_packages_path, 'PySide6/Qt/lib')
linux_lib = '/usr/lib/x86_64-linux-gnu'
nss_lib = '/usr/lib/x86_64-linux-gnu'  # NSS libraries location
gtk_lib = '/usr/lib/x86_64-linux-gnu'  # GTK libraries location
db_lib = '/usr/lib/x86_64-linux-gnu'   # Database libraries location
cuda_lib = '/usr/local/cuda-11/lib64'  # CUDA libraries location

a = Analysis(
    [join(airunner_path, 'main.py')],
    pathex=[
        join(base_path, 'src'),
    ],
    binaries=[
        (join(site_packages_path, 'tiktoken/_tiktoken.cpython-310-x86_64-linux-gnu.so'), '.'),
        (join(cudnn_lib, 'libcudnn_adv.so.9'), '.'),
        (join(cudnn_lib, 'libcudnn_cnn.so.9'), '.'),
        (join(cudnn_lib, 'libcudnn_engines_precompiled.so.9'), '.'),
        (join(cudnn_lib, 'libcudnn_engines_runtime_compiled.so.9'), '.'),
        (join(cudnn_lib, 'libcudnn_graph.so.9'), '.'),
        (join(cudnn_lib, 'libcudnn_heuristic.so.9'), '.'),
        (join(cudnn_lib, 'libcudnn_ops.so.9'), '.'),
        (join(cudnn_lib, 'libcudnn.so.9'), '.'),
        (join(pyside_lib, 'libQt6XcbQpa.so.6'), '.'),
        (join(pyside_lib, 'libQt6DBus.so.6'), '.'),
        (join(pyside_lib, 'libQt6Widgets.so.6'), '.'),
        (join(pyside_lib, 'libQt6Gui.so.6'), '.'),
        (join(pyside_lib, 'libQt6Core.so.6'), '.'),
        (join(linux_lib, 'libpython3.10.so.1.0'), '.'),
        (join(linux_lib, 'libxcb.so.1.1.0'), '.'),
        (join(linux_lib, 'libxkbcommon-x11.so.0.0.0'), '.'),
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
        (join(linux_lib, 'libpq.so.5'), '.'),
        (join(linux_lib, 'libodbc.so.2'), '.'),
        (join(linux_lib, 'libmysqlclient.so.21'), '.'),
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
        # CUDA libraries
        ('/home/appuser/.local/local/lib/python3.10/dist-packages/nvidia/cublas/lib/libcublas.so.11', '.'),
        ('/home/appuser/.local/local/lib/python3.10/dist-packages/nvidia/cusparse/lib/libcusparse.so.11', '.'),
        ('/home/appuser/.local/local/lib/python3.10/dist-packages/nvidia/cuda_runtime/lib/libcudart.so.11.0', '.'),
        ('/home/appuser/.local/local/lib/python3.10/dist-packages/nvidia/cublas/lib/libcublasLt.so.11', '.'),
        # Qt Virtual Keyboard
        # (join(pyside_lib, 'libQt6VirtualKeyboardSettings.so.6'), '.'),
    ],
    datas=[
        (join(airunner_path, 'alembic.ini'), 'airunner'),
        (join(site_packages_path, 'inflect'), 'inflect'),
        (join(site_packages_path, 'controlnet_aux'), 'controlnet_aux'),
        (join(site_packages_path, 'diffusers'), 'diffusers'),
        (join(site_packages_path, 'tiktoken'), 'tiktoken'),
        (join(site_packages_path, 'tiktoken_ext'), 'tiktoken_ext'),
        (join(site_packages_path, 'pydantic'), 'pydantic'),
        (join(site_packages_path, 'nvidia'), 'nvidia'),
        (join(site_packages_path, 'llama_index'), 'llama_index'),
        (join(site_packages_path, 'PySide6'), 'PySide6'),
        (join(site_packages_path, 'PySide6/Qt/plugins/platforms'), 'platforms'),
        (join(airunner_path, 'alembic'), 'airunner/alembic'),
        (join(airunner_path, 'alembic.ini'), '.'),
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
        'diffusers.loaders',
        'diffusers.loaders.ip_adapter',
        'diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion',
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
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
