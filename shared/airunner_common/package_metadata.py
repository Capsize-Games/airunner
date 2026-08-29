"""Canonical build metadata for every AIRunner package surface.

This module is the single source of truth for package versions, shared
requirements and console-script entry points. The ``services`` and ``native``
package surfaces both read their ``setuptools`` metadata from here so the two
can no longer drift from each other (architecture audit finding O1).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


VERSION = "6.0.0"
# Supply-chain hardening (issue #2036): the archive URL is hash-pinned so a
# tampered or moved tag cannot be substituted. Digest computed from the
# current v1.0.0 tarball (curl -sL <url> | sha256sum).
FACEHUGGERSHIELD_REQUIREMENT = (
    "facehuggershield @ "
    "https://github.com/Capsize-Games/facehuggershield/"
    "archive/refs/tags/v1.0.0.tar.gz"
    "#sha256=3430bb3363def8d0097a903ca106a4e944ff4a36f5a6fd374f06970090723482"
)

# The project is GPL-3.0-only (issue #2058): the repo-root LICENSE file, every
# ``license=`` metadata field and these PyPI classifiers must agree. Vendored
# MIT/Apache-2.0 components (melo, openvoice, z_image) are compatible with GPL
# distribution; see THIRD_PARTY_NOTICES.md.
LICENSE_CLASSIFIERS = [
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
]

# The shared package lives at <repo>/shared/airunner_common, so the repo root
# is two parents up (``shared`` and the repo root itself) in a checkout. The
# published sdist carries its own README.md at the sdist root (parents[1],
# via shared/MANIFEST.in), and an installed wheel has no README at all, so
# fall back instead of crashing at import time (issue #2061).
def _resolve_readme() -> str:
    module_dir = Path(__file__).resolve().parent
    for candidate in (
        module_dir.parents[2] / "README.md",  # repo checkout
        module_dir.parents[1] / "README.md",  # sdist root
    ):
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    # Installed wheel: no README ships with the runtime package. The wheel's
    # long_description was already baked from the sdist README at build time,
    # so a short placeholder here is only a defensive fallback.
    return "AI Runner shared foundation package."


README = _resolve_readme()

DEVELOPMENT_REQUIREMENTS = [
    "pytest",
    "pytest-timeout",
    "responses>=0.25.0",
    "coverage==7.8.0",
    "black==26.3.1",
    "pyinstaller==6.12.0",
    "flake8==7.2.0",
    "mypy==1.16.0",
    "autoflake==2.3.1",
    "pandas>=2.0.0",
    "pyarrow>=14.0.0",
    "tqdm>=4.0.0",
]

# ---------------------------------------------------------------------------
# Services package surface
# ---------------------------------------------------------------------------
CORE_REQUIREMENTS = [
    "numpy==2.2.5",
    "packaging>=24.0",
    "pillow==12.2.0",
    "pydantic>=2.7,<3.0",
    "nltk>=3.9.1",
    "alembic==1.13.2",
    "sqlalchemy==2.0.38",
    "jinja2==3.1.6",
    "pyyaml==6.0.2",
    "python-dotenv==1.2.2",
    "fastapi==0.115.0",
    "python-multipart>=0.0.27",
    "uvicorn[standard]==0.34.0",
    # Runtime deps declared in issue #2040 (previously undeclared).
    # psutil: model_management/hardware_profiler.py and
    #         llm/managers/tools/autonomous_control_insight_tools.py
    # pandas: api/routes/geolocation.py, eval/mixins/loader_mixin.py,
    #         utils/location/get_lat_lon.py (API route -> core)
    "psutil>=5.9.0",
    "pandas>=2.0.0",
]

# PyTorch is pinned to the exact stable cu129 wheel line so it aligns with
# the Docker base image nvidia/cuda:12.9.1-devel-ubuntu24.04 (issues #2036
# and #2041). Install with:
#     --index-url https://download.pytorch.org/whl/cu129
# CPU fallback (documented): use the +cpu index instead:
#     --index-url https://download.pytorch.org/whl/cpu
ML_RUNTIME_REQUIREMENTS = [
    "torch==2.13.0+cu129",
    "torchvision==0.28.0+cu129",
    "torchaudio==2.11.0+cu129",
    "accelerate==1.14.0",
    "huggingface-hub>=1.5.0,<2.0",
    "tokenizers==0.22.2",
    "optimum==1.25.1",
]

# Concrete CUDA runtime wheel pin (issue #2036). The bare
# "nvidia-cuda-runtime" name is a moving meta-package; the cu12 wheel is
# the concrete variant matching the Dockerfile's CUDA 12.9 base image.
NVIDIA_REQUIREMENTS = ["nvidia-cuda-runtime-cu12==12.9.79"]

HUGGINGFACE_REQUIREMENTS = [
    "diffusers==0.38.0",
    "controlnet_aux==0.0.10",
    "safetensors==0.8.0",
    "kornia",
    "timm",
    "compel==2.4.0",
    "transformers==5.8.1",
    "datasets==4.0.0",
]

ART_REQUIREMENTS = [
    "DeepCache==0.1.1",
    "tomesd==0.1.3",
    "gguf==0.17.1",
]

LLM_NATIVE_REQUIREMENTS = [
    "llama-cpp-python==0.3.21",
    "bitsandbytes==0.46.1",
    "sentence_transformers==5.6.1",
    "cryptography==46.0.7",
    "sumy==0.11.0",
    "sentencepiece==0.2.1",
    "lingua-language-detector==2.1.0",
    "markdown==3.8.1",
    "libzim==3.7.0",
    "mistral_common>=1.8.5",
    "rank-bm25>=0.2.2",
    "llama-cloud==0.1.23",
    "langchain-core==1.3.3",
    "langchain-huggingface==1.2.2",
    # langgraph 1.0.8 is the newest 1.0.x that still permits
    # langgraph-prebuilt 1.0.7; every prebuilt >=1.0.8 imports
    # ExecutionInfo/ServerInfo from langgraph.runtime, which does not exist
    # in the 1.0.x core (only >=1.2). langgraph 1.0.9/1.0.10 require
    # prebuilt>=1.0.8, which makes the set unresolvable. See services/setup.py.
    "langgraph==1.0.8",
    "langsmith>=0.8.0",
    "langchain-ollama==1.0.0",
    "langchain-text-splitters==1.1.2",
    "EbookLib==0.19",
    "mobi==0.4.1",
    "pypdf>=5.6.0",
    # Runtime dep declared in issue #2040 (previously undeclared):
    # bs4 is used by llm/managers/agent/document_loader.py and
    # llm/managers/agent/mixins/rag_lifecycle_mixin.py.
    "beautifulsoup4>=4.12.0",
]

LLM_WEATHER_REQUIREMENTS = [
    "requests-cache==1.2.1",
    "retry-requests==2.0.0",
    "openmeteo_requests==1.4.0",
    # Runtime dep declared in issue #2040 (previously undeclared):
    # openmeteo_sdk is imported by
    # llm/managers/agent/weather_mixin.py.
    "openmeteo_sdk>=1.22.0",
]

STT_NATIVE_REQUIREMENTS = ["sounddevice==0.5.1"]

TTS_REQUIREMENTS = [
    "inflect==7.5.0",
    "pycountry==24.6.1",
    "librosa==0.11.0",
    # Bound torchcodec to the pinned torch 2.13.x line (issue #2041).
    "torchcodec>=0.8.0,<0.10",
]

OPENVOICE_REQUIREMENTS = [
    "librosa==0.11.0",
    "pydub==0.25.1",
    "wavmark==0.0.3",
    "eng_to_ipa==0.0.2",
    "inflect==7.5.0",
    "unidecode==1.4.0",
    "langid==1.1.6",
]

MELOTTS_REQUIREMENTS = [
    "txtsplit==1.0.0",
    "num2words==0.5.14",
    "g2p_en==2.1.0",
    "anyascii==0.3.2",
    "loguru==0.7.3",
]

OPENVOICE_CN_REQUIREMENTS = [
    "pypinyin==0.54.0",
    "jieba==0.42.1",
    "cn2an==0.5.23",
]

OPENVOICE_JP_REQUIREMENTS = [
    "unidic_lite==1.0.8",
    "unidic==1.1.0",
    "mecab-python3==1.0.10",
    "fugashi==1.4.0",
    "pykakasi==2.3.0",
]

OPENVOICE_KR_REQUIREMENTS = [
    "jamo==0.4.1",
    "python-mecab-ko==1.3.7",
    "python-mecab-ko-dic==2.1.1.post2",
]

OPENVOICE_TW_REQUIREMENTS = ["g2pkk>=0.1.2"]

GRUUT_SUPPORT_REQUIREMENTS = [
    "gruut[de,es,fr]==2.4.0",
    "networkx==3.4.2",
]

SEARCH_REQUIREMENTS = [
    "ddgs>=9.0.0",
    "aiohttp>=3.13.4",
    "google-api-python-client>=2.170.0",
    "wikipedia>=1.4.0",
    "scrapy==2.14.2",
    "trafilatura==2.0.0",
]

COMPUTER_USE_REQUIREMENTS = [
    "pyautogui>=0.9.54",
    "pyscreeze>=1.0.1",
    "python-xlib>=0.33;platform_system=='Linux'",
    "pygetwindow>=0.0.9",
]

SYSTEM_DEP_EXTRAS = {"openvoice_jp", "openvoice_kr"}

SERVICE_CONSOLE_SCRIPTS = [
    "airunner-daemon=airunner_services.daemon:main",
    "airunner-headless=airunner_services.bin.airunner_headless:main",
    "airunner-service=airunner_services.bin.airunner_service:main",
    "airunner-generate-migration="
    "airunner_services.bin.generate_migration:main",
    "airunner-hf-download=airunner_services.bin.airunner_hf_download:main",
    "airunner-civitai-download="
    "airunner_services.bin.airunner_civitai_download:main",
]

# ---------------------------------------------------------------------------
# Native package surface
# ---------------------------------------------------------------------------
# Issue #2042: the GUI package owns the primary `airunner` console script
# (setup.py entry_points). The native launcher is exposed as `airunner-native`
# so installing airunner-native no longer shadows/duplicates the GUI command.
NATIVE_CONSOLE_SCRIPTS = [
    "airunner-native=airunner_native.launcher:main",
]

NATIVE_BASE_REQUIREMENTS = [
    f"airunner-common=={VERSION}",
    f"airunner-services=={VERSION}",
    FACEHUGGERSHIELD_REQUIREMENT,
]


def _find_packages(package_source_dir: str) -> list[str]:
    """Return the packages under a source dir without importing setuptools.

    setuptools is a build-time dependency and must not be required at runtime
    by the published airunner-common wheel (issue #2061), so ``find_packages``
    is imported lazily inside this helper instead of at module level.
    """
    from setuptools import find_packages  # noqa: PLC0415  # build-time only

    return find_packages(package_source_dir)


def unique_requirements(*groups: list[str]) -> list[str]:
    """Return one stable dependency list with duplicates removed."""
    dependencies: list[str] = []
    for group in groups:
        dependencies.extend(group)
    return list(dict.fromkeys(dependencies))


def _base_extras_require() -> dict[str, list[str]]:
    """Return the non-aggregate service extras."""
    return {
        "core": [],
        "nvidia": NVIDIA_REQUIREMENTS,
        "linux": [],
        "development": DEVELOPMENT_REQUIREMENTS,
        "dev": DEVELOPMENT_REQUIREMENTS,
        "art": ART_REQUIREMENTS,
        "huggingface": HUGGINGFACE_REQUIREMENTS,
        "llm-native": unique_requirements(
            ML_RUNTIME_REQUIREMENTS,
            LLM_NATIVE_REQUIREMENTS,
        ),
        "stt-native": STT_NATIVE_REQUIREMENTS,
        "art-python": unique_requirements(
            ML_RUNTIME_REQUIREMENTS,
            HUGGINGFACE_REQUIREMENTS,
            ART_REQUIREMENTS,
        ),
        "llm": unique_requirements(
            ML_RUNTIME_REQUIREMENTS,
            LLM_NATIVE_REQUIREMENTS,
            STT_NATIVE_REQUIREMENTS,
            ["pyttsx3==2.91"],
        ),
        "llm_weather": LLM_WEATHER_REQUIREMENTS,
        "llm-weather": LLM_WEATHER_REQUIREMENTS,
        "tts": TTS_REQUIREMENTS,
        "tts-python": unique_requirements(
            ML_RUNTIME_REQUIREMENTS,
            TTS_REQUIREMENTS,
            ["pyttsx3==2.91"],
            OPENVOICE_REQUIREMENTS,
            MELOTTS_REQUIREMENTS,
            OPENVOICE_CN_REQUIREMENTS,
            OPENVOICE_TW_REQUIREMENTS,
            GRUUT_SUPPORT_REQUIREMENTS,
        ),
        "openvoice": OPENVOICE_REQUIREMENTS,
        "melotts": MELOTTS_REQUIREMENTS,
        "openvoice_cn": OPENVOICE_CN_REQUIREMENTS,
        "openvoice_jp": OPENVOICE_JP_REQUIREMENTS,
        "openvoice_kr": OPENVOICE_KR_REQUIREMENTS,
        "openvoice_tw": OPENVOICE_TW_REQUIREMENTS,
        "gruut_support": GRUUT_SUPPORT_REQUIREMENTS,
        "search": SEARCH_REQUIREMENTS,
        "computer_use": COMPUTER_USE_REQUIREMENTS,
        "computer-use": COMPUTER_USE_REQUIREMENTS,
    }


def _aggregate_extra(
    extras_require: dict[str, list[str]],
    *extra_names: str,
) -> list[str]:
    """Return one flattened aggregate extra dependency list."""
    dependencies: list[str] = []
    for extra_name in extra_names:
        dependencies.extend(extras_require[extra_name])
    return list(dict.fromkeys(dependencies))


def _aggregate_extras_require(
    extras_require: dict[str, list[str]],
) -> dict[str, list[str]]:
    """Return the aggregate service extras."""
    headless = _aggregate_extra(
        extras_require,
        "llm-native",
        "stt-native",
        "art-python",
        "tts-python",
    )
    aggregate_require = {**extras_require, "headless": headless}
    desktop = _aggregate_extra(
        aggregate_require,
        "headless",
        "llm_weather",
        "search",
        "computer_use",
        "nvidia",
        "linux",
    )
    aggregate_require["desktop"] = desktop
    all_native = _aggregate_extra(
        aggregate_require,
        "desktop",
        *sorted(SYSTEM_DEP_EXTRAS),
    )
    return {
        "headless": headless,
        "desktop": desktop,
        "all": desktop,
        "all_dev": _aggregate_extra(
            {**aggregate_require, "all": desktop},
            "all",
            "development",
        ),
        "all_native": all_native,
        "all_dev_native": _aggregate_extra(
            {**aggregate_require, "all_native": all_native},
            "all_native",
            "development",
        ),
        "windows": _aggregate_extra(
            aggregate_require,
            "headless",
            "llm_weather",
            "search",
            "computer_use",
            "nvidia",
        ),
    }


def build_services_extras_require() -> dict[str, list[str]]:
    """Return the extras map for the service package surface."""
    extras_require = _base_extras_require()
    extras_require.update(_aggregate_extras_require(extras_require))
    return extras_require


def build_services_setup_kwargs(*, package_source_dir: str) -> dict[str, Any]:
    """Return the setuptools metadata for the service package surface."""
    install_requires = [
        f"airunner-common=={VERSION}",
        FACEHUGGERSHIELD_REQUIREMENT,
        *CORE_REQUIREMENTS,
    ]
    return {
        "name": "airunner-services",
        "version": VERSION,
        "author": "Capsize LLC",
        "description": "AIRunner headless service package",
        "long_description": README,
        "long_description_content_type": "text/markdown",
        "license": "GPL-3.0-only",
        "classifiers": LICENSE_CLASSIFIERS,
        "author_email": "contact@capsizegames.com",
        "url": "https://github.com/Capsize-Games/airunner",
        "package_dir": {"": package_source_dir},
        # Imported lazily: setuptools is a build-time dependency and must not
        # be required at runtime by the published airunner-common wheel
        # (issue #2061). No setup.py calls these helpers anymore (the
        # services/native metadata is vendored statically, issue #2038).
        "packages": _find_packages(package_source_dir),
        "python_requires": ">=3.13.3",
        "install_requires": install_requires,
        "extras_require": build_services_extras_require(),
        "package_data": {
            "airunner_services": [
                "assets/reference_speakers/*.wav",
            ],
            "airunner_services.bin": ["*.sh"],
            "airunner_services.database": [
                "alembic.ini",
                "alembic/*.py",
                "alembic/*.mako",
                "alembic/versions/*.py",
            ],
        },
        "include_package_data": True,
        "entry_points": {"console_scripts": SERVICE_CONSOLE_SCRIPTS},
    }


def build_native_extras_require() -> dict[str, list[str]]:
    """Return optional extras for the native package surface."""
    gui_requirements = [f"airunner=={VERSION}"]
    return {
        "development": DEVELOPMENT_REQUIREMENTS,
        "dev": DEVELOPMENT_REQUIREMENTS,
        "gui": gui_requirements,
        "desktop": gui_requirements,
    }


def build_native_setup_kwargs(*, package_source_dir: str) -> dict[str, Any]:
    """Return the setuptools metadata for the native package surface."""
    return {
        "name": "airunner-native",
        "version": VERSION,
        "author": "Capsize LLC",
        "description": "AIRunner native launcher and bundle tooling",
        "long_description": README,
        "long_description_content_type": "text/markdown",
        "license": "GPL-3.0-only",
        "classifiers": LICENSE_CLASSIFIERS,
        "author_email": "contact@capsizegames.com",
        "url": "https://github.com/Capsize-Games/airunner",
        "package_dir": {"": package_source_dir},
        "packages": _find_packages(package_source_dir),
        "python_requires": ">=3.13.3",
        "install_requires": NATIVE_BASE_REQUIREMENTS,
        "extras_require": build_native_extras_require(),
        "include_package_data": True,
        "entry_points": {"console_scripts": NATIVE_CONSOLE_SCRIPTS},
    }


__all__ = [
    "ART_REQUIREMENTS",
    "COMPUTER_USE_REQUIREMENTS",
    "CORE_REQUIREMENTS",
    "DEVELOPMENT_REQUIREMENTS",
    "FACEHUGGERSHIELD_REQUIREMENT",
    "GRUUT_SUPPORT_REQUIREMENTS",
    "HUGGINGFACE_REQUIREMENTS",
    "LICENSE_CLASSIFIERS",
    "LLM_NATIVE_REQUIREMENTS",
    "LLM_WEATHER_REQUIREMENTS",
    "MELOTTS_REQUIREMENTS",
    "ML_RUNTIME_REQUIREMENTS",
    "NATIVE_BASE_REQUIREMENTS",
    "NATIVE_CONSOLE_SCRIPTS",
    "NVIDIA_REQUIREMENTS",
    "OPENVOICE_CN_REQUIREMENTS",
    "OPENVOICE_JP_REQUIREMENTS",
    "OPENVOICE_KR_REQUIREMENTS",
    "OPENVOICE_REQUIREMENTS",
    "OPENVOICE_TW_REQUIREMENTS",
    "SEARCH_REQUIREMENTS",
    "SERVICE_CONSOLE_SCRIPTS",
    "STT_NATIVE_REQUIREMENTS",
    "SYSTEM_DEP_EXTRAS",
    "TTS_REQUIREMENTS",
    "VERSION",
    "build_native_extras_require",
    "build_native_setup_kwargs",
    "build_services_extras_require",
    "build_services_setup_kwargs",
    "unique_requirements",
]
