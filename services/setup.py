"""Canonical setup.py for the services package surface.

The build metadata below is vendored statically so ``services/`` can be
built without installing airunner_common first (issue #2038); that
package now lives in its own repository
(https://github.com/Capsize-Games/airunner-common, issue #2197). Its
own VERSION/FACEHUGGERSHIELD_REQUIREMENT/LICENSE_CLASSIFIERS are the
values worth keeping in sync here when they change; everything else
below (the requirement groups, extras, console scripts) is specific to
this package surface and independently authoritative.
"""

from pathlib import Path

from setuptools import find_packages, setup

VERSION = "6.1.3"

# The project is GPL-3.0-only (issue #2058): the repo-root LICENSE file, every
# ``license=`` metadata field and these PyPI classifiers must agree. Mirrored
# from airunner_common/package_metadata.py in Capsize-Games/airunner-common.
LICENSE_CLASSIFIERS = [
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
]

# Supply-chain hardening (issue #2036). This was a hash-pinned GitHub archive
# URL, but PyPI rejects any distribution carrying a PEP 440 direct reference
# ("400 Can't have direct dependency"), so no such package can ever be
# published. facehuggershield 1.0.0 is on PyPI, so depend on it by version.
#
# This does not weaken the original intent. That pin existed so "a tampered or
# moved tag cannot be substituted" -- but a git tag *can* be moved, which is
# exactly why it needed a digest. A PyPI release cannot: a version is immutable
# once uploaded and can only be yanked, never replaced. Installs also verify
# PyPI's own hashes over TLS. For a fully hash-locked install, pin digests in a
# requirements file at deploy time, which is where hash-locking belongs --
# install_requires cannot express it for consumers anyway.
FACEHUGGERSHIELD_REQUIREMENT = "facehuggershield==1.0.0"

# Per-package README used as long_description (mirrors native/). The
# repo-root README is not part of this package's sdist, so a wheel built from
# the sdist would fail to resolve it (issue #2061); each published package
# carries its own README.
README = (Path(__file__).resolve().parent / "README.md").read_text(
    encoding="utf-8"
)

DEVELOPMENT_REQUIREMENTS = [
    "pytest",
    "pytest-timeout",
    "responses>=0.25.0",
    # starlette/fastapi TestClient (services HTTP-surface tests) needs httpx;
    # it is otherwise only pulled in transitively by the llm-native extra.
    "httpx>=0.27",
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
    # langgraph-prebuilt >=1.0.8 imports ExecutionInfo/ServerInfo from
    # langgraph.runtime, which only exists in langgraph core >=1.2. Against
    # 1.0.x core that import crashes the tool-calling path ("cannot import
    # name 'ExecutionInfo'"). langgraph 1.0.9/1.0.10 require prebuilt>=1.0.8,
    # so the only self-consistent 1.0.x set is core 1.0.8 + prebuilt 1.0.7
    # (1.0.8 still allows prebuilt>=1.0.7). Pinning core 1.0.10 + prebuilt
    # 1.0.5 satisfied neither pip's resolver nor the runtime.
    "langgraph==1.0.8",
    "langgraph-prebuilt==1.0.7",
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

# The MeloTTS/OpenVoice fork moved to its own published package,
# airunner-tts-vendor (issue #2195, part of #2185):
# github.com/Capsize-Games/airunner-tts-vendor. Its own
# pyproject.toml is the source of truth for the underlying
# third-party pins now; these extras just select the matching slice
# of that package (zh/jp/kr/tw/gruut), mirroring the extras split it
# publishes itself
# (docs/architecture/versioning-and-compatibility-policy.md, #2191).
# torch/torchaudio/transformers stay out of this pin -- ML_RUNTIME_
# REQUIREMENTS below already supplies those for tts-python.
OPENVOICE_REQUIREMENTS = ["airunner-tts-vendor~=0.1"]

MELOTTS_REQUIREMENTS = ["airunner-tts-vendor~=0.1"]

OPENVOICE_CN_REQUIREMENTS = ["airunner-tts-vendor[zh]~=0.1"]

OPENVOICE_JP_REQUIREMENTS = ["airunner-tts-vendor[jp]~=0.1"]

OPENVOICE_KR_REQUIREMENTS = ["airunner-tts-vendor[kr]~=0.1"]

OPENVOICE_TW_REQUIREMENTS = ["airunner-tts-vendor[tw]~=0.1"]

GRUUT_SUPPORT_REQUIREMENTS = ["airunner-tts-vendor[gruut]~=0.1"]

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


def build_services_setup_kwargs(*, package_source_dir: str) -> dict[str, object]:
    """Return the setuptools metadata for the service package surface."""
    install_requires = [
        # airunner-common is independently versioned in its own repository
        # now (issue #2197, https://github.com/Capsize-Games/airunner-common),
        # so a compatible-release pin per the versioning policy (#2191)
        # instead of an exact lockstep VERSION pin. Floor is 6.1.7, the
        # release that added the shared for_action generation table
        # (issue #2225) on top of 6.1.6's shared LLMRequest (#2221) and
        # 6.1.5's LLMResponse (#2188) -- this package imports all three
        # directly and cannot start on an older release.
        "airunner-common~=6.1.7",
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
        "packages": find_packages(package_source_dir),
        "python_requires": ">=3.13.3",
        "install_requires": install_requires,
        "extras_require": build_services_extras_require(),
        "package_data": {
            "airunner_services": [
                "assets/reference_speakers/*.wav",
            ],
            "airunner_services.bin": ["*.sh"],
            "airunner_services.content_safety": [
                "data/*.dat",
            ],
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


setup(**build_services_setup_kwargs(package_source_dir="src"))
