"""Packaging constraint tests (GitHub issue #2057).

The pinned ``torch==2.13.0+cu129`` wheel's runtime metadata requires
``setuptools<82``. Every build-system file that carries a setuptools
requirement must therefore stay below 82, or ``pip check`` fails on any
install that includes the ML runtime. This file source-scans the packaging
files so a future bump (e.g. PR #2022 wanting ``>=84``) is caught in CI.
"""

from __future__ import annotations

import re
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

#: Packaging files whose [build-system] requirements include setuptools.
_BUILD_SYSTEM_FILES = (
    _PROJECT_ROOT / "pyproject.toml",
    _PROJECT_ROOT / "services" / "pyproject.toml",
    _PROJECT_ROOT / "native" / "pyproject.toml",
)

def test_build_system_setuptools_below_82() -> None:
    """Every build-system file must keep setuptools below 82 while torch is
    pinned below 2.14 (issue #2057)."""
    assert _build_system_files_exist()

    for path in _BUILD_SYSTEM_FILES:
        source = path.read_text(encoding="utf-8")
        match = re.search(r'setuptools\s*>=?\s*([0-9]+(?:\.[0-9]+)*)', source)
        assert match is not None, (
            f"{path.name} carries no setuptools requirement"
        )
        version_str = match.group(1)
        major = int(version_str.split(".")[0])
        assert major < 82, (
            f"{path.name} requests setuptools>={version_str} (>=82) which "
            "conflicts with the pinned torch wheel requiring setuptools<82 "
            "(issue #2057)"
        )
        # The requirement must also carry an explicit upper bound <82.
        assert re.search(r'setuptools\s*>=?\s*[0-9]+(?:\.[0-9]+)*\s*,\s*<82', source), (
            f"{path.name} must pin setuptools with an explicit <82 upper "
            "bound (issue #2057)"
        )


#: Each of these setup.py files vendors its own DEVELOPMENT_REQUIREMENTS
#: copy (issue #2038/#2197 -- no more single canonical
#: shared/airunner_common/package_metadata.py source to scan instead).
_DEV_REQUIREMENTS_FILES = (
    _PROJECT_ROOT / "setup.py",
    _PROJECT_ROOT / "services" / "setup.py",
    _PROJECT_ROOT / "native" / "setup.py",
)


def test_no_setuptools_pin_above_82_in_dev_requirements() -> None:
    """DEVELOPMENT_REQUIREMENTS must not request setuptools>=82 either."""
    for path in _DEV_REQUIREMENTS_FILES:
        source = path.read_text(encoding="utf-8")
        for line in source.splitlines():
            if "setuptools" not in line:
                continue
            match = re.search(
                r'setuptools\s*>=?\s*([0-9]+(?:\.[0-9]+)*)', line
            )
            if match and int(match.group(1).split(".")[0]) >= 82:
                raise AssertionError(
                    f"{path}: DEVELOPMENT_REQUIREMENTS pins "
                    f"setuptools>={match.group(1)} which conflicts with "
                    "torch's setuptools<82 requirement (issue #2057)"
                )


def _build_system_files_exist() -> bool:
    """Sanity guard: every expected packaging file must be present."""
    for path in _BUILD_SYSTEM_FILES:
        assert path.is_file(), f"missing packaging file {path}"
    return True
