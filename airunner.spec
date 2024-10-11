# -*- mode: python ; coding: utf-8 -*-

import site
import os

# Get the directory of the spec file
if os.getenv('DOCKER_ENV') == 'true':
    root_path = os.path.dirname(os.path.abspath('airunner.spec'))
    base_path = os.path.join(root_path, 'airunner')
    site_packages_path = "/home/appuser/.local/lib/python3.10/site-packages/"
    dist = "/app/dist"
else:
    root_path = os.path.dirname(os.path.abspath('airunner.spec'))
    base_path = root_path
    site_packages_path = site.getsitepackages()[0]
    dist = "./dist"

# Set the path to the airunner package
airunner_path = os.path.join(base_path, "src/airunner")

a = Analysis(
    [os.path.join(airunner_path, 'main.py')],
    pathex=[
        os.path.join(base_path, 'src'),
    ],
    binaries=[
        (os.path.join(site_packages_path, 'tiktoken/_tiktoken.cpython-310-x86_64-linux-gnu.so'), '.'),
        (os.path.join(site_packages_path, 'nvidia/cudnn/lib/libcudnn_adv.so.9'), '.'),
        (os.path.join(site_packages_path, 'nvidia/cudnn/lib/libcudnn_cnn.so.9'), '.'),
        (os.path.join(site_packages_path, 'nvidia/cudnn/lib/libcudnn_engines_precompiled.so.9'), '.'),
        (os.path.join(site_packages_path, 'nvidia/cudnn/lib/libcudnn_engines_runtime_compiled.so.9'), '.'),
        (os.path.join(site_packages_path, 'nvidia/cudnn/lib/libcudnn_graph.so.9'), '.'),
        (os.path.join(site_packages_path, 'nvidia/cudnn/lib/libcudnn_heuristic.so.9'), '.'),
        (os.path.join(site_packages_path, 'nvidia/cudnn/lib/libcudnn_ops.so.9'), '.'),
        (os.path.join(site_packages_path, 'nvidia/cudnn/lib/libcudnn.so.9'), '.'),
        (os.path.join(site_packages_path, 'PySide6/Qt/lib/libQt6XcbQpa.so.6'), '.'),
        (os.path.join(site_packages_path, 'PySide6/Qt/lib/libQt6DBus.so.6'), '.'),
        (os.path.join(site_packages_path, 'PySide6/Qt/lib/libQt6Widgets.so.6'), '.'),
        (os.path.join(site_packages_path, 'PySide6/Qt/lib/libQt6Gui.so.6'), '.'),
        (os.path.join(site_packages_path, 'PySide6/Qt/lib/libQt6Core.so.6'), '.'),
        ('/usr/lib/x86_64-linux-gnu/libpython3.10.so', '.'),
        ('/usr/lib/x86_64-linux-gnu/libxcb.so.1.1.0', '.'),
        ('/usr/lib/x86_64-linux-gnu/libxkbcommon-x11.so.0.0.0', '.'),
    ],
    datas=[
        (os.path.join(airunner_path, 'alembic.ini'), '.'),
        (os.path.join(site_packages_path, 'inflect'), 'inflect'),
        (os.path.join(site_packages_path, 'controlnet_aux'), 'controlnet_aux'),
        (os.path.join(site_packages_path, 'diffusers'), 'diffusers'),
        (os.path.join(site_packages_path, 'tiktoken'), 'tiktoken'),
        (os.path.join(site_packages_path, 'tiktoken_ext'), 'tiktoken_ext'),
        (os.path.join(site_packages_path, 'pydantic'), 'pydantic'),
        (os.path.join(site_packages_path, 'xformers'), 'xformers'),
        (os.path.join(site_packages_path, 'nvidia'), 'nvidia'),
        (os.path.join(site_packages_path, 'llama_index'), 'llama_index'),
        (os.path.join(site_packages_path, 'PySide6'), 'PySide6'),
        (os.path.join(site_packages_path, 'PySide6/Qt/plugins/platforms'), 'platforms'),
        # Add other data files or directories here
    ],
    hiddenimports=[
        'airunner',
        'airunner.data.models',
        'airunner.data.models.settings_models',
        'airunner.utils.db.column_exists',
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
        'torch',
        'torch.jit',
        'torch.jit._script',
        'torch.jit.frontend',
        'torch._sources',
        'xformers',
        'xformers.ops',
        'xformers.ops.fmha',
        'xformers.ops.fmha.triton_splitk',
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
        'PySide6',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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

import shutil
images_path = os.path.join(airunner_path, 'images/')
styles_path = os.path.join(airunner_path, 'styles/')
alembic_path = os.path.join(airunner_path, 'alembic/')
data_path = os.path.join(airunner_path, 'data/')
punkt_path = os.path.join(root_path, 'lib/tokenizers/punkt/')
print(f"Copy images from {images_path}...")
shutil.copytree(images_path, os.path.join(base_path, os.path.join(dist, 'airunner/_internal/airunner/images/')))
print(f"Copy styles from {styles_path}...")
shutil.copytree(styles_path, os.path.join(base_path, os.path.join(dist, 'airunner/_internal/airunner/styles/')))
print(f"Copy alembic from {alembic_path}...")
shutil.copytree(alembic_path, os.path.join(base_path, os.path.join(dist, 'airunner/_internal/alembic/')))
print(f"Copy data from {data_path}...")
shutil.copytree(data_path, os.path.join(base_path, os.path.join(dist, 'airunner/data/')))
print(f"Copy punkt from {punkt_path}...")
shutil.copytree(punkt_path, os.path.join(base_path, os.path.join(dist, 'airunner/_internal/llama_index/core/_static/nltk_cache/tokenizers/punkt')))
