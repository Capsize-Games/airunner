"""Check that in-tree package edges follow the repository version policy."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _release_version(path: Path) -> str:
    source = path.read_text(encoding="utf-8")
    match = re.search(r'^_RELEASE_VERSION = "([^"]+)"$', source, re.MULTILINE)
    assert match is not None, f"missing release version in {path}"
    return match.group(1)


def test_airunner_services_source_dependency_tracks_its_independent_version() -> None:
    root_setup = (ROOT / "setup.py").read_text(encoding="utf-8")
    service_version = _release_version(ROOT / "services" / "setup.py")

    requirement = re.search(
        r'^\s*"airunner-services(~=|==)([^"]+)"\s*,?$',
        root_setup,
        re.MULTILINE,
    )
    assert requirement is not None, "missing AIRunner services dependency"
    assert requirement.group(1) == "~=", (
        "development installations use a compatible services range; only "
        "the release lockfile pins the tested exact pair"
    )
    assert requirement.group(2) == service_version
