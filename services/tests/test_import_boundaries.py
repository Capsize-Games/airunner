"""Tests for scripts/check_import_boundaries.py (issue #2193).

The dependency-order check guards CI: this is what would have caught
the defects #2186 (services importing the desktop app), #2189
(production importing the benchmark harness) and #2190 (a vendored
library importing the application's database models) before they
reached ``main``. No repository in #2185's Phase 1 onward may be
created before this check is green and wired into CI -- it is wired
here, the same pattern
``services/tests/test_third_party_notices.py`` already established
for ``scripts/check_third_party_notices.py`` (issue #2059).
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.check_import_boundaries import run_check  # noqa: E402
from scripts.import_boundary_allowlist import ALLOWLIST  # noqa: E402


def test_the_real_tree_has_no_import_boundary_violations() -> None:
    """The repository passes its own dependency-order rules."""
    problems = run_check(repo_root=_PROJECT_ROOT)
    assert problems == [], "\n".join(problems)


def test_allowlist_entries_are_individually_justified() -> None:
    """No wildcard, no threshold: every entry names a real file/line.

    #2193's own requirement. This does not assert the allowlist is
    empty (Phase 0 is not fully merged as one commit), only that
    every entry that exists still points at a file and line that
    actually contains that exact import -- an entry that no longer
    matches anything is stale and should be deleted, not left behind.
    """
    stale = []
    for rel_path, lineno, imported in ALLOWLIST:
        full_path = _PROJECT_ROOT / rel_path
        if not full_path.is_file():
            stale.append((rel_path, lineno, imported, "file missing"))
            continue
        lines = full_path.read_text(encoding="utf-8").splitlines()
        if lineno > len(lines) or imported not in lines[lineno - 1]:
            stale.append((rel_path, lineno, imported, "line drifted"))
    assert stale == []


def test_services_importing_airunner_is_caught(tmp_path) -> None:
    """A function-level import counts exactly like a module-level one.

    Regression for the four originally-lazy get_qsettings sites
    #2186 found: a checker that only looked at module-level imports
    would have missed every one of them.
    """
    import textwrap

    from scripts.check_import_boundaries import run_check as _run

    fake_repo = tmp_path / "repo"
    services_dir = fake_repo / "services" / "src" / "airunner_services"
    services_dir.mkdir(parents=True)
    (services_dir / "offender.py").write_text(
        textwrap.dedent(
            """
            def lazy():
                import airunner.enums  # a function-level import
            """
        )
    )
    problems = _run(repo_root=fake_repo)
    assert len(problems) == 1
    assert "offender.py" in problems[0]
    assert "airunner.enums" in problems[0]
