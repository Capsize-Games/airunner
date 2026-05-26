"""Canonical build metadata for the service package surface."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from setuptools import find_packages


VERSION = "6.0.0"
FACEHUGGERSHIELD_REQUIREMENT = (
    "facehuggershield @ "
    "https://github.com/Capsize-Games/facehuggershield/"
    "archive/refs/tags/v1.0.0.tar.gz"
)

README = (
    Path(__file__).resolve().parents[1] / "README.md"
).read_text(encoding="utf-8")

CORE_REQUIREMENTS = [
    "numpy==2.2.5",
    "packaging>=24.0",
    "pillow==12.2.0",
    "alembic==1.13.2",
    "aiosqlite==0.21.0",
    "sqlalchemy==2.0.38",
    "psycopg[binary]>=3.2.0",
    "etils[epath]==1.12.2",
    "jinja2==3.1.6",
    "pyyaml==6.0.2",
    "python-dotenv==1.2.2",
]

ML_RUNTIME_REQUIREMENTS = [
    "torch",
    "torchvision",
    "torchaudio",
    "accelerate==1.7.0",
    "huggingface-hub>=1.5.0,<2.0",
    "tokenizers==0.22.0",
    "optimum==1.25.1",
]

NVIDIA_REQUIREMENTS = ["nvidia-cuda-runtime"]

HUGGINGFACE_REQUIREMENTS = [
    "diffusers==0.38.0",
    "controlnet_aux==0.0.10",
    "safetensors==0.6.2",
    "kornia",
    "timm",
    "compel==2.1.1",
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
    "bitsandbytes==0.45.5",
    "sentence_transformers==3.4.1",
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
    "langchain-huggingface==1.0.0",
    "langgraph==1.0.10",
    "langsmith>=0.8.0",
    "langchain-ollama==1.0.0",
    "langchain-text-splitters==1.1.2",
    "EbookLib==0.19",
    "mobi==0.4.1",
    "pypdf>=5.6.0",
]

STT_NATIVE_REQUIREMENTS = ["sounddevice==0.5.1"]

LLM_WEATHER_REQUIREMENTS = [
    "requests-cache==1.2.1",
    "retry-requests==2.0.0",
    "openmeteo_requests==1.4.0",
]

TTS_REQUIREMENTS = [
    "inflect==7.5.0",
    "pycountry==24.6.1",
    "librosa==0.11.0",
    "torchcodec>=0.8.0",
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


def build_extras_require() -> dict[str, list[str]]:
    """Return the extras map for the service package surface."""
    extras_require = _base_extras_require()
    extras_require.update(_aggregate_extras_require(extras_require))
    return extras_require


def build_setup_kwargs(*, package_source_dir: str) -> dict[str, Any]:
    """Return the setuptools metadata for the service package surface."""
    install_requires = [
        f"airunner-model=={VERSION}",
        f"airunner-api=={VERSION}",
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
        "license": "Apache-2.0",
        "author_email": "contact@capsizegames.com",
        "url": "https://github.com/Capsize-Games/airunner",
        "package_dir": {"": package_source_dir},
        "packages": find_packages(package_source_dir),
        "python_requires": ">=3.13.3",
        "install_requires": install_requires,
        "extras_require": build_extras_require(),
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


__all__ = ["SERVICE_CONSOLE_SCRIPTS", "VERSION", "build_setup_kwargs"]