"""Reviewed sibling and runtime-artifact pins for issue #2200.

Issue #2200 (release orchestration) treats the pins in
``services/setup.py`` and ``native/setup.py`` as reviewed inputs: the
values below were reviewed together with the active Linux release lock
(``package/constraints-linux-nvidia-cu129-linux-release.txt``). Changing
a version here is a re-review event, not a drive-by edit, so every
reviewed literal is asserted exactly. A bump must update the assertion,
the lock, and the review records together.

This complements ``test_active_lock_covers_release_profile_requirements``
(which proves setup.py and the lock agree with each other, but would
accept a jointly-bumped pair) and the whole-file digests in
``release-inputs.json``/``core-input-readiness.json`` (which prove the
lock files did not drift, but say nothing about the setup.py side).

Static analysis only: setup.py sources are exec-loaded without running
their final ``setup()`` call. No installs, no network, no GPU/models.
"""

from __future__ import annotations

import json
import re
import types
from pathlib import Path

import pytest
from packaging.requirements import Requirement

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SERVICES_SETUP = _PROJECT_ROOT / "services" / "setup.py"
_NATIVE_SETUP = _PROJECT_ROOT / "native" / "setup.py"
_RELEASE_INPUTS = (
    _PROJECT_ROOT / "release-planning/services/release-inputs.json"
)
_PIN_LINE = re.compile(r"^([A-Za-z0-9_.\-]+)==([^\s\\;]+)")


def _load_setup_module(path: Path, setup_call: str) -> types.ModuleType:
    """Execute a setup.py without running its final setup() call."""
    text = path.read_text(encoding="utf-8")
    text = text[: text.rindex(setup_call)]
    module = types.ModuleType(f"sibling_pins_{path.parent.name}")
    module.__file__ = str(path)
    exec(compile(text, str(path), "exec"), module.__dict__)
    return module


def _services() -> types.ModuleType:
    """Load the services setup module without side effects."""
    return _load_setup_module(
        _SERVICES_SETUP,
        "\nsetup(**build_services_setup_kwargs",
    )


def _native() -> types.ModuleType:
    """Load the native setup module without side effects."""
    return _load_setup_module(
        _NATIVE_SETUP,
        "\nsetup(**build_native_setup_kwargs",
    )


def _normalise(name: str) -> str:
    """Normalize a distribution name for comparison."""
    return re.sub(r"[-_.]+", "-", name).lower()


#: Reviewed torch/cu129 runtime wheel pins (services/setup.py:114-121).
_REVIEWED_ML_RUNTIME = [
    "torch==2.13.0+cu129",
    "torchvision==0.28.0+cu129.capsize.1",
    "torchaudio==2.11.0+cu129.capsize.1",
    "accelerate==1.14.0+capsize.1",
    "huggingface-hub>=1.5.0,<2.0",
    "tokenizers==0.23.1+capsize.1",
    "optimum==1.25.1",
]

#: Reviewed concrete CUDA runtime wheel pin (services/setup.py:127).
_REVIEWED_NVIDIA = ["nvidia-cuda-runtime-cu12==12.9.79"]

#: Reviewed art/huggingface runtime pins (services/setup.py:129-137).
_REVIEWED_HUGGINGFACE = [
    "diffusers==0.38.0",
    "safetensors==0.8.0",
    "kornia",
    "timm",
    "compel==2.4.0+capsize.1",
    "transformers==5.22.0",
    "datasets==5.0.1",
]

#: Reviewed art-pipeline runtime pins (services/setup.py:139-143).
_REVIEWED_ART = [
    "DeepCache==0.1.1",
    "tomesd==0.1.3",
    "gguf==0.17.1",
]

#: Reviewed RAG document/embedding pins (services/setup.py:158-166).
_REVIEWED_RAG = [
    "sentence_transformers==5.6.1",
    "libzim==3.7.0+capsize.2",
    "langchain-huggingface==1.2.2",
    "langchain-text-splitters==1.1.2",
    "EbookLib==0.20",
    "mobi==0.4.1",
    "pypdf>=6.21.4",
]

#: Reviewed llm-native runtime pins (services/setup.py:168-190).
_REVIEWED_LLM_NATIVE = [
    "llama-cpp-python==0.3.21+capsize.3",
    "bitsandbytes==0.46.1",
    "cryptography==50.0.2",
    "sumy==0.11.0",
    "sentencepiece==0.2.1",
    "lingua-language-detector==2.1.0+capsize.1",
    "markdown==3.11.2",
    "mistral_common>=1.8.5",
    "rank-bm25>=0.2.2",
    "llama-cloud==0.1.23",
    "langchain-core==1.4.7",
    "langgraph==1.2.14",
    "langgraph-prebuilt==1.1.0",
    "langsmith>=0.8.0",
    "langchain-ollama==1.0.0",
    "beautifulsoup4>=4.12.0",
]

#: Reviewed weather runtime pins (services/setup.py:192-200).
_REVIEWED_LLM_WEATHER = [
    "requests-cache==1.2.1",
    "retry-requests==2.0.0",
    "openmeteo_requests==1.4.0",
    "openmeteo_sdk>=1.22.0",
]

#: Reviewed STT runtime pin (services/setup.py:202).
_REVIEWED_STT_NATIVE = ["sounddevice==0.5.1"]

#: Reviewed TTS runtime pins (services/setup.py:204-214).
_REVIEWED_TTS = [
    "inflect==7.5.0",
    "pycountry==24.6.1",
    "librosa==0.11.0",
    "soundfile==0.14.0",
    "torchcodec>=0.12.0,<0.18",
]

#: Reviewed search runtime pins (services/setup.py:240-249).
_REVIEWED_SEARCH = [
    "ddgs>=9.0.0",
    "aiohttp>=3.13.4",
    "google-api-python-client>=2.170.0",
    "scrapy==2.17.0",
    "Twisted==26.10.0",
    "trafilatura==2.0.0",
]

#: Reviewed sibling tts-vendor slices (services/setup.py:226-238).
_REVIEWED_TTS_VENDOR_EXTRAS = {
    "openvoice": ["airunner-tts-vendor~=0.1"],
    "melotts": ["airunner-tts-vendor~=0.1"],
    "openvoice_cn": ["airunner-tts-vendor[zh]~=0.1"],
    "openvoice_jp": ["airunner-tts-vendor[jp]~=0.1"],
    "openvoice_kr": ["airunner-tts-vendor[kr]~=0.1"],
    "openvoice_tw": ["airunner-tts-vendor[tw]~=0.1"],
    "gruut_support": ["airunner-tts-vendor[gruut]~=0.1"],
}

#: Reviewed native launcher service bounds (native/setup.py:89-100).
_REVIEWED_NATIVE_SERVICE_BOUND = "airunner-services>=6.1.5,<7"

#: Reviewed foundation sibling pin (services/setup.py:470,
#: native/setup.py:75).
_REVIEWED_COMMON_PIN = "airunner-common~=6.1.8"


def test_ml_runtime_pins_are_reviewed_revisions() -> None:
    """The torch/cu129 wheel line keeps its reviewed revisions."""
    assert _services().ML_RUNTIME_REQUIREMENTS == _REVIEWED_ML_RUNTIME


def test_nvidia_runtime_pin_is_reviewed_revision() -> None:
    """The concrete CUDA runtime wheel keeps its reviewed revision."""
    assert _services().NVIDIA_REQUIREMENTS == _REVIEWED_NVIDIA


def test_huggingface_runtime_pins_are_reviewed_revisions() -> None:
    """The art/huggingface slice keeps its reviewed revisions."""
    assert _services().HUGGINGFACE_REQUIREMENTS == _REVIEWED_HUGGINGFACE


def test_art_runtime_pins_are_reviewed_revisions() -> None:
    """The art-pipeline runtime slice keeps its reviewed revisions."""
    assert _services().ART_REQUIREMENTS == _REVIEWED_ART


def test_rag_runtime_pins_are_reviewed_revisions() -> None:
    """The RAG document/embedding slice keeps its reviewed revisions."""
    assert _services().RAG_REQUIREMENTS == _REVIEWED_RAG


def test_llm_native_runtime_pins_are_reviewed_revisions() -> None:
    """The llm-native runtime slice keeps its reviewed revisions."""
    assert _services().LLM_NATIVE_REQUIREMENTS == _REVIEWED_LLM_NATIVE


def test_weather_stt_tts_search_pins_are_reviewed_revisions() -> None:
    """Weather/STT/TTS/search slices keep their reviewed revisions."""
    module = _services()
    assert module.LLM_WEATHER_REQUIREMENTS == _REVIEWED_LLM_WEATHER
    assert module.STT_NATIVE_REQUIREMENTS == _REVIEWED_STT_NATIVE
    assert module.TTS_REQUIREMENTS == _REVIEWED_TTS
    assert module.SEARCH_REQUIREMENTS == _REVIEWED_SEARCH


def test_services_common_pin_is_reviewed_compatible_release() -> None:
    """The services base keeps its reviewed airunner-common pin."""
    kwargs = _services().build_services_setup_kwargs(package_source_dir="src")
    matches = [
        raw
        for raw in kwargs["install_requires"]
        if Requirement(raw).name == "airunner-common"
    ]
    assert matches == [_REVIEWED_COMMON_PIN]


def test_tts_vendor_extras_pin_reviewed_range() -> None:
    """Each tts-vendor slice keeps its reviewed compatible-release pin."""
    extras = _services().build_services_extras_require()
    for extra, reviewed in _REVIEWED_TTS_VENDOR_EXTRAS.items():
        assert extras[extra] == reviewed, extra


def test_native_launcher_service_bounds_are_reviewed() -> None:
    """Launcher extras keep the reviewed services floor and major cap."""
    extras = _native().build_native_extras_require()
    for extra in ("services", "daemon", "gui", "desktop"):
        assert extras[extra] == [_REVIEWED_NATIVE_SERVICE_BOUND], extra


def _active_lock_pins() -> dict[str, str]:
    """Map normalized distribution name to locked version."""
    manifest = json.loads(_RELEASE_INPUTS.read_text(encoding="utf-8"))
    profile = manifest["release_profile"]
    if profile["lock_status"] == "generation_pending":
        pytest.skip(
            "linux-release lock is being regenerated; reviewed setup.py "
            "literals above still hold, lock agreement waits for the lock"
        )
    assert profile["lock_status"] == "ready", profile["lock_status"]
    lock = _PROJECT_ROOT / profile["active_lock"]
    pins: dict[str, str] = {}
    for line in lock.read_text(encoding="utf-8").splitlines():
        match = _PIN_LINE.match(line)
        if match:
            pins[_normalise(match.group(1))] = match.group(2)
    assert pins, "active lock has no pins"
    return pins


def test_reviewed_exact_pins_agree_with_active_lock() -> None:
    """Every reviewed == pin resolves to the identical locked version."""
    pins = _active_lock_pins()
    reviewed = [
        *_REVIEWED_ML_RUNTIME,
        *_REVIEWED_NVIDIA,
        *_REVIEWED_HUGGINGFACE,
        *_REVIEWED_ART,
        *_REVIEWED_RAG,
        *_REVIEWED_LLM_NATIVE,
        *_REVIEWED_LLM_WEATHER,
        *_REVIEWED_STT_NATIVE,
        *_REVIEWED_TTS,
        *_REVIEWED_SEARCH,
    ]
    checked = 0
    for raw in reviewed:
        requirement = Requirement(raw)
        assert requirement.url is None, raw
        name = _normalise(requirement.name)
        assert name in pins, f"reviewed {raw} is missing from the active lock"
        if not str(requirement.specifier):
            continue
        if raw.count("==") == 1 and all(
            op not in str(requirement.specifier) for op in (">=", "<=", ">", "<", "~=")
        ):
            assert pins[name] == str(requirement.specifier).lstrip("="), (
                f"reviewed {raw} drifts from locked {name}=={pins[name]}"
            )
            checked += 1
        else:
            assert requirement.specifier.contains(
                pins[name], prereleases=True
            ), f"locked {name}=={pins[name]} violates reviewed {raw}"
    assert checked > 0, "no reviewed == pins were checked against the lock"


def test_reviewed_sibling_edges_agree_with_active_lock() -> None:
    """Sibling edges resolve to the lock; deferred siblings stay out."""
    pins = _active_lock_pins()
    manifest = json.loads(_RELEASE_INPUTS.read_text(encoding="utf-8"))
    assert Requirement(_REVIEWED_COMMON_PIN).specifier.contains(
        pins["airunner-common"], prereleases=True
    )
    for excluded in manifest["release_profile"]["excludes"]:
        assert _normalise(excluded) not in pins, (
            f"deferred {excluded} must not appear in the active lock"
        )
    for local in ("airunner-services", "airunner-native"):
        assert local not in pins, (
            f"local root {local} must not appear in the active lock"
        )
