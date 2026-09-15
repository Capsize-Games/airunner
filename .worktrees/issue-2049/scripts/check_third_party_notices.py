"""Verify every vendored package ships a LICENSE and a THIRD_PARTY_NOTICES entry.

Searches for ``vendor`` directories under ``services/src`` and ``src``. For
each immediate subdirectory that contains Python sources (a "vendored
package"), it asserts:

1. The subdirectory contains a ``LICENSE`` file.
2. The subdirectory is listed in the top-level ``THIRD_PARTY_NOTICES.md``
   by its repository-relative path.

Run directly (``python scripts/check_third_party_notices.py``) it exits
non-zero and prints each problem. It is also wired into the CI test suite via
``services/tests/test_third_party_notices.py`` (issue #2059).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_VENDOR_SEARCH_BASES = ("services/src", "src")
_NOTICES_FILENAME = "THIRD_PARTY_NOTICES.md"


def _repo_relative(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def find_vendor_roots(repo_root: Path) -> list[Path]:
    """Return every directory named ``vendor`` under services/src and src."""
    roots: list[Path] = []
    for base_rel in _VENDOR_SEARCH_BASES:
        base = repo_root / base_rel
        if base.is_dir():
            roots.extend(
                candidate
                for candidate in sorted(base.rglob("vendor"))
                if candidate.is_dir()
            )
    return roots


def find_vendored_packages(vendor_root: Path) -> list[Path]:
    """Return immediate subdirs of a vendor root that contain Python sources."""
    if not vendor_root.is_dir():
        return []
    return sorted(
        child
        for child in vendor_root.iterdir()
        if child.is_dir() and any(child.rglob("*.py"))
    )


def run_check(*, repo_root: Path | None = None) -> list[str]:
    """Return human-readable problems; an empty list means the check passed."""
    root = (repo_root or _REPO_ROOT).resolve()
    notices = root / _NOTICES_FILENAME
    problems: list[str] = []

    if not notices.is_file():
        problems.append(f"missing {_NOTICES_FILENAME} at repository root ({notices})")
    notices_text = notices.read_text(encoding="utf-8") if notices.is_file() else ""

    packages = [
        pkg
        for vendor_root in find_vendor_roots(root)
        for pkg in find_vendored_packages(vendor_root)
    ]
    if not packages:
        problems.append("no vendored packages found under services/src or src")
        return problems

    for pkg in packages:
        rel = _repo_relative(pkg, root)
        if not (pkg / "LICENSE").is_file():
            problems.append(f"{rel}: missing LICENSE file")
        if rel not in notices_text:
            problems.append(f"{rel}: not listed in {_NOTICES_FILENAME}")

    return problems


def main() -> int:
    """CLI entry point; returns a process exit code."""
    problems = run_check()
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        print(
            f"\n{len(problems)} third-party notice problem(s) found.",
            file=sys.stderr,
        )
        return 1
    print(
        "OK: every vendored package has a LICENSE "
        "and a THIRD_PARTY_NOTICES entry."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
