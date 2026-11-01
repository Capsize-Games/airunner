"""Build backend pin and historical P02 lock evidence.

The active isolated build requirements use the reviewed setuptools 84.2.1
backend. The preserved historical desktop runtime lock still records
setuptools 81.0.0 and is not an active release lock.
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

def test_build_system_uses_reviewed_setuptools_backend() -> None:
    """Pin every active build system to the reviewed backend revision."""
    assert _build_system_files_exist()

    for path in _BUILD_SYSTEM_FILES:
        source = path.read_text(encoding="utf-8")
        assert '"setuptools==84.2.1"' in source, (
            f"{path.name} must pin the reviewed setuptools 84.2.1 backend"
        )


#: Each of these setup.py files vendors its own DEVELOPMENT_REQUIREMENTS
#: copy (issue #2038/#2197 -- no more single canonical
#: shared/airunner_common/package_metadata.py source to scan instead).
_DEV_REQUIREMENTS_FILES = (
    _PROJECT_ROOT / "services" / "setup.py",
    _PROJECT_ROOT / "native" / "setup.py",
)


def test_setup_scripts_do_not_add_setuptools_runtime_requirement() -> None:
    """Setup scripts must leave the backend out of runtime dependencies."""
    for path in _DEV_REQUIREMENTS_FILES:
        source = path.read_text(encoding="utf-8")
        for line in source.splitlines():
            if "setuptools" not in line:
                continue
            assert not re.search(r"setuptools\s*[<=>~!]", line), (
                f"{path}: build backend appears as a runtime requirement"
            )


def test_historical_desktop_lock_keeps_its_hashed_snapshot() -> None:
    """Keep historical lock evidence without treating it as active config."""
    source = _HISTORICAL_RUNTIME_LOCK.read_text(encoding="utf-8")
    match = re.search(r"(?m)^setuptools==([0-9]+(?:\.[0-9]+)*) \\", source)
    assert match is not None, "Linux runtime lock must pin setuptools exactly"
    locked = tuple(int(part) for part in match.group(1).split("."))
    assert locked == (81, 0, 0), (
        "historical desktop lock should retain its original setuptools pin"
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
