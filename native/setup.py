"""Canonical setup.py for the native package surface.

The build metadata below is vendored statically so ``native/`` can be built
without installing the shared ``airunner_common`` package first (issue #2038).
``shared/airunner_common/package_metadata.py`` remains the canonical runtime
source of the same requirement groups; keep the values in this file in sync
with it when a dependency changes.
"""

from pathlib import Path

from setuptools import find_packages, setup

VERSION = "6.1.3"

# The project is GPL-3.0-only (issue #2058): the repo-root LICENSE file, every
# ``license=`` metadata field and these PyPI classifiers must agree. Mirrored
# from shared/airunner_common/package_metadata.py (LICENSE_CLASSIFIERS).
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

# Per-package README used as long_description (mirrors services/). The
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
