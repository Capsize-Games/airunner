"""Canonical build metadata for the service package surface."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from setuptools import find_packages

from package_deps import (
    CORE_REQUIREMENTS,
    FACEHUGGERSHIELD_REQUIREMENT,
    SERVICE_CONSOLE_SCRIPTS,
    SYSTEM_DEP_EXTRAS,
    ART_REQUIREMENTS,
    COMPUTER_USE_REQUIREMENTS,
    DEVELOPMENT_REQUIREMENTS,
    GRUUT_SUPPORT_REQUIREMENTS,
    HUGGINGFACE_REQUIREMENTS,
    LLM_NATIVE_REQUIREMENTS,
    LLM_WEATHER_REQUIREMENTS,
    MELOTTS_REQUIREMENTS,
    ML_RUNTIME_REQUIREMENTS,
    NVIDIA_REQUIREMENTS,
    OPENVOICE_REQUIREMENTS,
    OPENVOICE_CN_REQUIREMENTS,
    OPENVOICE_JP_REQUIREMENTS,
    OPENVOICE_KR_REQUIREMENTS,
    OPENVOICE_TW_REQUIREMENTS,
    SEARCH_REQUIREMENTS,
    STT_NATIVE_REQUIREMENTS,
    TTS_REQUIREMENTS,
)

VERSION = "6.0.0"

README = (Path(__file__).resolve().parents[1] / "README.md").read_text(
    encoding="utf-8"
)


def unique_requirements(*groups: list[str]) -> list[str]:
    """Return one stable dependency list with duplicates removed."""
    dependencies: list[str] = []
    for group in groups:
        dependencies.extend(group)
    return list(dict.fromkeys(dependencies))


# Pre-combined extras so _base_extras_require fits in 40 body lines.
_LLM_NATIVE_EXTRA = unique_requirements(
    ML_RUNTIME_REQUIREMENTS,
    LLM_NATIVE_REQUIREMENTS,
)
_ART_PYTHON_EXTRA = unique_requirements(
    ML_RUNTIME_REQUIREMENTS,
    HUGGINGFACE_REQUIREMENTS,
    ART_REQUIREMENTS,
)
_LLM_EXTRA = unique_requirements(
    ML_RUNTIME_REQUIREMENTS,
    LLM_NATIVE_REQUIREMENTS,
    STT_NATIVE_REQUIREMENTS,
    ["pyttsx3==2.91"],
)
_TTS_PYTHON_EXTRA = unique_requirements(
    ML_RUNTIME_REQUIREMENTS,
    TTS_REQUIREMENTS,
    ["pyttsx3==2.91"],
    OPENVOICE_REQUIREMENTS,
    MELOTTS_REQUIREMENTS,
    OPENVOICE_CN_REQUIREMENTS,
    OPENVOICE_TW_REQUIREMENTS,
    GRUUT_SUPPORT_REQUIREMENTS,
)


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
        "llm-native": _LLM_NATIVE_EXTRA,
        "stt-native": STT_NATIVE_REQUIREMENTS,
        "art-python": _ART_PYTHON_EXTRA,
        "llm": _LLM_EXTRA,
        "llm_weather": LLM_WEATHER_REQUIREMENTS,
        "llm-weather": LLM_WEATHER_REQUIREMENTS,
        "tts": TTS_REQUIREMENTS,
        "tts-python": _TTS_PYTHON_EXTRA,
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
    server_extras = _aggregate_extra(
        extras_require, "llm-native", "stt-native",
        "art-python", "tts-python",
    )
    aggregate_require = {**extras_require, "server": server_extras}
    desktop = _aggregate_extra(
        aggregate_require, "server", "llm_weather",
        "search", "computer_use", "nvidia", "linux",
    )
    aggregate_require["desktop"] = desktop
    all_native = _aggregate_extra(
        aggregate_require, "desktop",
        *sorted(SYSTEM_DEP_EXTRAS),
    )
    all_dev = _aggregate_extra(
        {**aggregate_require, "all": desktop},
        "all", "development",
    )
    all_dev_native = _aggregate_extra(
        {**aggregate_require, "all_native": all_native},
        "all_native", "development",
    )
    return {"server": server_extras,
            "desktop": desktop,
            "all": desktop,
            "all_dev": all_dev,
            "all_native": all_native,
            "all_dev_native": all_dev_native,
            "windows": _aggregate_extra(
                aggregate_require, "server", "llm_weather",
                "search", "computer_use", "nvidia",
            )}


def build_extras_require() -> dict[str, list[str]]:
    """Return the extras map for the service package surface."""
    extras_require = _base_extras_require()
    extras_require.update(_aggregate_extras_require(extras_require))
    return extras_require


def build_setup_kwargs(*, package_source_dir: str) -> dict[str, Any]:
    """Return the setuptools metadata for the service package surface."""
    install_requires = [
        FACEHUGGERSHIELD_REQUIREMENT,
        *CORE_REQUIREMENTS,
    ]
    return {
        "name": "airunner-services",
        "version": VERSION,
        "author": "Capsize LLC",
        "description": "AIRunner service package",
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
