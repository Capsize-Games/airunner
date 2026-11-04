"""Check in-tree launcher/service compatibility after the GUI retirement."""

from __future__ import annotations

import re
from pathlib import Path

from packaging.specifiers import SpecifierSet

ROOT = Path(__file__).resolve().parents[2]


def test_launcher_accepts_the_in_tree_service_version() -> None:
    """The launcher service extras must accept this release's daemon."""
    service_source = (ROOT / "services/setup.py").read_text()
    native_source = (ROOT / "native/setup.py").read_text()
    version = re.search(
        r'^_RELEASE_VERSION = "([^"]+)"$', service_source, re.MULTILINE
    )
    assert version is not None
    requirements = re.findall(
        r'"airunner-services([^"\n]+)"', native_source
    )
    assert requirements, "launcher must declare its service dependency"
    for requirement in requirements:
        assert version.group(1) in SpecifierSet(requirement)


def test_debian_package_matches_service_release_version() -> None:
    """The installed health version must match the Debian package version."""
    service_source = (ROOT / "services/setup.py").read_text()
    version = re.search(
        r'^_RELEASE_VERSION = "([^\"]+)"$', service_source, re.MULTILINE
    )
    assert version is not None
    changelog = (ROOT / "debian/changelog").read_text()
    package = re.match(r"airunner \(([^)]+)\)", changelog)
    assert package is not None
    upstream_version = package.group(1).rsplit("-", 1)[0]
    assert upstream_version == version.group(1)
