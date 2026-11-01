"""Build-system bounds and historical P02 lock evidence (#2057).

The repository's isolated build requirements are pinned to
``setuptools>=80.9,<82`` and the preserved historical runtime lock stays in
that range. The active linux-release lock is not yet generated. The installed
``torch==2.13.0+cu129`` metadata inspected for this audit
declares ``setuptools>=77.0.3`` without an upper bound; the <82 policy is a
repository compatibility pin, not a torch runtime metadata requirement.
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
_HISTORICAL_RUNTIME_LOCK = (
    _PROJECT_ROOT
    / "package"
    / "constraints-linux-nvidia-cu129-historical-desktop.txt"
)

def test_build_system_setuptools_below_82() -> None:
    """Enforce the repository's build-system setuptools cap (issue #2057)."""
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
            "conflicts with the repository's setuptools<82 compatibility "
            "policy (issue #2057)"
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
                    "the repository's setuptools<82 compatibility policy "
                    "(issue #2057)"
                )


def test_historical_runtime_lock_setuptools_fits_build_system_range() -> None:
    """The historical hash set stays within the recorded build pin."""
    source = _HISTORICAL_RUNTIME_LOCK.read_text(encoding="utf-8")
    match = re.search(r"(?m)^setuptools==([0-9]+(?:\.[0-9]+)*) \\", source)
    assert match is not None, "Linux runtime lock must pin setuptools exactly"
    locked = tuple(int(part) for part in match.group(1).split("."))
    assert (80, 9) <= locked < (82,), (
        f"runtime setuptools {match.group(1)} is outside the guarded "
        ">=80.9,<82 range"
    )
    start = match.start()
    end = re.search(r"(?m)^[A-Za-z0-9_.-]+==", source[match.end():])
    block = source[start:]
    if end is not None:
        block = source[start:match.end() + end.start()]
    hashes = re.findall(r"--hash=sha256:[0-9a-f]{64}", block)
    assert len(hashes) >= 2, "setuptools lock entry needs wheel and sdist hashes"


def _build_system_files_exist() -> bool:
    """Sanity guard: every expected packaging file must be present."""
    for path in _BUILD_SYSTEM_FILES:
        assert path.is_file(), f"missing packaging file {path}"
    return True
