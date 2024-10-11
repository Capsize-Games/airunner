# -*- mode: python ; coding: utf-8 -*-

import site
import os

# Get the site-packages path
site_packages_path = site.getsitepackages()[0]

a = Analysis(
    ['./src/airunner/main.py'],
    pathex=[
        './src',
    ],
    binaries=[
        ('/usr/lib/x86_64-linux-gnu/libpython3.10.so', '.'),
        ('./venv/lib/python3.10/site-packages/tiktoken/_tiktoken.cpython-310-x86_64-linux-gnu.so', '.'),
        ('/usr/lib/x86_64-linux-gnu/libcudnn.so.8', '.'),  # Add libcudnn shared libraries
        ('/usr/lib/x86_64-linux-gnu/libcudnn_adv_infer.so.8', '.'),
        ('/usr/lib/x86_64-linux-gnu/libcudnn_adv_train.so.8', '.'),
        ('/usr/lib/x86_64-linux-gnu/libcudnn_cnn_infer.so.8', '.'),
        ('/usr/lib/x86_64-linux-gnu/libcudnn_cnn_train.so.8', '.'),
        ('/usr/lib/x86_64-linux-gnu/libcudnn_ops_infer.so.8', '.'),
        ('/usr/lib/x86_64-linux-gnu/libcudnn_ops_train.so.8', '.'),
        (os.path.join(site_packages_path, 'nvidia/cudnn/lib/libcudnn_adv.so.9'), '.'),
        (os.path.join(site_packages_path, 'nvidia/cudnn/lib/libcudnn_cnn.so.9'), '.'),
        (os.path.join(site_packages_path, 'nvidia/cudnn/lib/libcudnn_engines_precompiled.so.9'), '.'),
        (os.path.join(site_packages_path, 'nvidia/cudnn/lib/libcudnn_engines_runtime_compiled.so.9'), '.'),
        (os.path.join(site_packages_path, 'nvidia/cudnn/lib/libcudnn_graph.so.9'), '.'),
        (os.path.join(site_packages_path, 'nvidia/cudnn/lib/libcudnn_heuristic.so.9'), '.'),
        (os.path.join(site_packages_path, 'nvidia/cudnn/lib/libcudnn_ops.so.9'), '.'),
        (os.path.join(site_packages_path, 'nvidia/cudnn/lib/libcudnn.so.9'), '.'),

    ],
    datas=[
        ('./src/airunner/alembic.ini', '.'),
        (os.path.join(site_packages_path, 'inflect'), 'inflect'),
        (os.path.join(site_packages_path, 'controlnet_aux'), 'controlnet_aux'),
        (os.path.join(site_packages_path, 'diffusers'), 'diffusers'),
        (os.path.join(site_packages_path, 'tiktoken'), 'tiktoken'),
        (os.path.join(site_packages_path, 'tiktoken_ext'), 'tiktoken_ext'),
        (os.path.join(site_packages_path, 'pydantic'), 'pydantic'),
        (os.path.join(site_packages_path, 'xformers'), 'xformers'),
        (os.path.join(site_packages_path, 'nvidia'), 'nvidia'),
        (os.path.join(site_packages_path, 'llama_index'), 'llama_index'),
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
shutil.copytree('./src/airunner/images/', './dist/airunner/_internal/airunner/images/')
shutil.copytree('./src/airunner/styles/', './dist/airunner/_internal/airunner/styles/')
shutil.copytree('./src/airunner/alembic/', './dist/airunner/_internal/alembic/')
shutil.copytree('./src/airunner/data/', './dist/airunner/data/')
shutil.copytree('./lib/tokenizers/punkt', './dist/airunner/_internal/llama_index/core/_static/nltk_cache/tokenizers/punkt')
