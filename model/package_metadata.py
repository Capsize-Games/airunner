"""Canonical build metadata for the model package surface."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from setuptools import find_packages


VERSION = "6.0.0"

README = (
    Path(__file__).resolve().parents[1] / "README.md"
).read_text(encoding="utf-8")

MODEL_REQUIREMENTS = [
    "pydantic>=2.7,<3.0",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
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


def build_extras_require() -> dict[str, list[str]]:
    """Return the model package extras map."""
    return {
        "development": DEVELOPMENT_REQUIREMENTS,
        "dev": DEVELOPMENT_REQUIREMENTS,
    }


def build_setup_kwargs(*, package_source_dir: str) -> dict[str, Any]:
    """Return the setuptools metadata for the model package surface."""
    return {
        "name": "airunner-model",
        "version": VERSION,
        "author": "Capsize LLC",
        "description": "AIRunner inference and runtime contract package",
        "long_description": README,
        "long_description_content_type": "text/markdown",
        "license": "Apache-2.0",
        "author_email": "contact@capsizegames.com",
        "url": "https://github.com/Capsize-Games/airunner",
        "package_dir": {"": package_source_dir},
        "packages": find_packages(package_source_dir),
        "python_requires": ">=3.13.3",
        "install_requires": MODEL_REQUIREMENTS,
        "extras_require": build_extras_require(),
        "include_package_data": True,
    }


__all__ = [
    "DEVELOPMENT_REQUIREMENTS",
    "MODEL_REQUIREMENTS",
    "VERSION",
    "build_setup_kwargs",
]