"""Tests for scripts/check_third_party_notices.py (GitHub issue #2059).

The notice check guards CI: every vendored package directory must ship a
LICENSE file and be listed in the top-level THIRD_PARTY_NOTICES.md. These
tests assert the real repo passes, that the known vendored packages are
actually discovered, and that the check fails when a LICENSE or a notice
entry is missing.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.check_third_party_notices import (  # noqa: E402
    find_vendored_packages,
    find_vendor_roots,
    run_check,
)


def test_vendored_packages_have_license_and_notices() -> None:
    """The real repo's vendored packages all pass the notice check."""
    problems = run_check(repo_root=_PROJECT_ROOT)
    assert problems == [], "\n".join(problems)


def test_script_discovers_the_known_vendored_packages() -> None:
    """Sanity check: the scan must actually see melo and openvoice."""
    vendor_roots = find_vendor_roots(_PROJECT_ROOT)
    assert vendor_roots, "no vendor/ directories discovered under services/src or src"
    packages = [
        pkg
        for vendor_root in vendor_roots
        for pkg in find_vendored_packages(vendor_root)
    ]
    names = {pkg.name for pkg in packages}
    assert {"melo", "openvoice"}.issubset(names)


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
