"""Canonical build metadata for the native package surface."""

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

NATIVE_CONSOLE_SCRIPTS = [
    "airunner=airunner_native.launcher:main",
    "airunner-build-end-user-bundle="
    "airunner_native.bin.build_end_user_bundle:main",
]

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

NATIVE_BASE_REQUIREMENTS = [
    f"airunner-model=={VERSION}",
    f"airunner-services=={VERSION}",
    FACEHUGGERSHIELD_REQUIREMENT,
]


def build_extras_require() -> dict[str, list[str]]:
    """Return optional extras for the native package surface."""
    gui_requirements = [f"airunner=={VERSION}"]
    return {
        "development": DEVELOPMENT_REQUIREMENTS,
        "dev": DEVELOPMENT_REQUIREMENTS,
        "gui": gui_requirements,
        "desktop": gui_requirements,
    }


def build_setup_kwargs(*, package_source_dir: str) -> dict[str, Any]:
    """Return the setuptools metadata for the native package surface."""
    return {
        "name": "airunner-native",
        "version": VERSION,
        "author": "Capsize LLC",
        "description": "AIRunner native launcher and bundle tooling",
        "long_description": README,
        "long_description_content_type": "text/markdown",
        "license": "Apache-2.0",
        "author_email": "contact@capsizegames.com",
        "url": "https://github.com/Capsize-Games/airunner",
        "package_dir": {"": package_source_dir},
        "packages": find_packages(package_source_dir),
        "python_requires": ">=3.13.3",
        "install_requires": NATIVE_BASE_REQUIREMENTS,
        "extras_require": build_extras_require(),
        "include_package_data": True,
        "entry_points": {"console_scripts": NATIVE_CONSOLE_SCRIPTS},
    }


__all__ = [
    "DEVELOPMENT_REQUIREMENTS",
    "NATIVE_BASE_REQUIREMENTS",
    "NATIVE_CONSOLE_SCRIPTS",
    "VERSION",
    "build_extras_require",
    "build_setup_kwargs",
]