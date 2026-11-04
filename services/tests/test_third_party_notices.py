"""Tests for scripts/check_third_party_notices.py (GitHub issue #2059).

The notice check guards CI: every vendored package directory must ship a
LICENSE file and be listed in the top-level THIRD_PARTY_NOTICES.md. melo
and openvoice, the packages that originally exercised this (installed
under a real ``vendor/`` directory here), moved to their own repository
(issue #2195, https://github.com/Capsize-Games/airunner-tts-vendor),
which documents their licensing itself instead. These tests assert the
real repo still passes (vacuously, with no vendor directories left) and
that the check fails when a LICENSE or a notice entry is missing, against
a synthetic fixture rather than real vendored code.
"""

from __future__ import annotations

import sys
import hashlib
import json

import pytest
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.check_third_party_notices import run_check  # noqa: E402


def test_vendored_packages_have_license_and_notices() -> None:
    """The real repo's vendored packages all pass the notice check."""
    problems = run_check(repo_root=_PROJECT_ROOT)
    assert problems == [], "\n".join(problems)


def _write_notice_stub(root: Path, *, listed: bool) -> None:
    """Create a minimal THIRD_PARTY_NOTICES.md in a temp repo root."""
    content = "# Third-Party Notices\n\n"
    if listed:
        content += (
            "## example_vendor\n\n"
            "Vendored location: "
            "`services/src/airunner_services/vendor/example_vendor`\n"
        )
    else:
        content += "## some other project\n\n"
    (root / "THIRD_PARTY_NOTICES.md").write_text(content, encoding="utf-8")


def test_missing_license_is_reported(tmp_path: Path) -> None:
    """A vendored package without a LICENSE file fails the check."""
    root = tmp_path
    pkg_dir = (
        root / "services" / "src" / "airunner_services" / "vendor" / "example_vendor"
    )
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    _write_notice_stub(root, listed=True)

    problems = run_check(repo_root=root)
    assert any("missing LICENSE" in problem for problem in problems)


def test_missing_notice_entry_is_reported(tmp_path: Path) -> None:
    """A vendored package absent from THIRD_PARTY_NOTICES.md fails the check."""
    root = tmp_path
    pkg_dir = (
        root / "services" / "src" / "airunner_services" / "vendor" / "example_vendor"
    )
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (pkg_dir / "LICENSE").write_text(
        "MIT License\n\nCopyright (c) 2024 Example\n", encoding="utf-8"
    )
    _write_notice_stub(root, listed=False)

    problems = run_check(repo_root=root)
    assert any("not listed" in problem for problem in problems)


@pytest.mark.parametrize("directory", ["watchfiles-rust-crates", "pydantic-core-rust-crates"])
def test_cargo_notice_payload_matches_reviewed_source_index(directory: str) -> None:
    """Detect missing or altered original notices before candidate assembly."""
    root = _PROJECT_ROOT / "packaging" / "licenses" / directory
    index = json.loads((root / f"{directory}.source.json").read_text())
    paths = set()
    crates = index["compiled_crates"] if directory == "watchfiles-rust-crates" else index["crates"]
    for crate in crates:
        assert crate["crate_archive_sha256"] == crate["registry_checksum"]
        assert crate["notices"], f"Missing notices for {crate['name']}"
        for notice in crate["notices"]:
            relative = Path(notice["bundle_path"])
            assert len(relative.parts) == 1 and not relative.is_absolute()
            path = root / relative
            assert not path.is_symlink()
            content = path.read_bytes()
            assert content and len(content) == notice["size"]
            assert hashlib.sha256(content).hexdigest() == notice["sha256"]
            paths.add(relative.name)
    if "package_license_notice" in index:
        notice = index["package_license_notice"]
        content = (root / notice["bundle_path"]).read_bytes()
        assert len(content) == notice["size"]
        assert hashlib.sha256(content).hexdigest() == notice["sha256"]
        paths.add(notice["bundle_path"])
    assert paths == {path.name for path in root.iterdir() if not path.name.endswith(".source.json")}
