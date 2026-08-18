"""Canonical setup.py for the native package surface.

The build metadata below is vendored statically so ``native/`` can be built
without installing the shared ``airunner_common`` package first (issue #2038).
``shared/airunner_common/package_metadata.py`` remains the canonical runtime
source of the same requirement groups; keep the values in this file in sync
with it when a dependency changes.
"""

from pathlib import Path

from setuptools import find_packages, setup

VERSION = "6.0.0"

# The project is GPL-3.0-only (issue #2058): the repo-root LICENSE file, every
# ``license=`` metadata field and these PyPI classifiers must agree. Mirrored
# from shared/airunner_common/package_metadata.py (LICENSE_CLASSIFIERS).
LICENSE_CLASSIFIERS = [
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
]

# Supply-chain hardening (issue #2036): the archive URL is hash-pinned so a
# tampered or moved tag cannot be substituted. Digest computed from the
# current v1.0.0 tarball (curl -sL <url> | sha256sum).
FACEHUGGERSHIELD_REQUIREMENT = (
    "facehuggershield @ "
    "https://github.com/Capsize-Games/facehuggershield/"
    "archive/refs/tags/v1.0.0.tar.gz"
    "#sha256=3430bb3363def8d0097a903ca106a4e944ff4a36f5a6fd374f06970090723482"
)

# The repo root is one parent up from native/setup.py (mirrors the shared
# package_metadata README which resolves from shared/airunner_common).
README = (Path(__file__).resolve().parents[1] / "README.md").read_text(
    encoding="utf-8"
)

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


def build_native_extras_require() -> dict[str, list[str]]:
    """Return optional extras for the native package surface."""
    gui_requirements = [f"airunner=={VERSION}"]
    return {
        "development": DEVELOPMENT_REQUIREMENTS,
        "dev": DEVELOPMENT_REQUIREMENTS,
        "gui": gui_requirements,
        "desktop": gui_requirements,
    }


def build_native_setup_kwargs(*, package_source_dir: str) -> dict[str, object]:
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
        "packages": find_packages(package_source_dir),
        "python_requires": ">=3.13.3",
        "install_requires": NATIVE_BASE_REQUIREMENTS,
        "extras_require": build_native_extras_require(),
        "include_package_data": True,
        "entry_points": {"console_scripts": NATIVE_CONSOLE_SCRIPTS},
    }


setup(**build_native_setup_kwargs(package_source_dir="src"))
