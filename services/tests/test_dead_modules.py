"""Tests for scripts/check_dead_modules.py (issue #2480).

The dead-module gate stops abandoned modules from accumulating: any
module nothing references must either be referenced or carry a
justified entry in ``scripts/dead_module_allowlist.py``. These tests
lock that contract the same way
``services/tests/test_import_boundaries.py`` locks the dependency-order
gate -- a green real-tree run, a stale-entry guard, and unit coverage
of every reference rule on synthetic trees.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

from scripts import check_dead_modules as gate  # noqa: E402
from scripts.dead_module_allowlist import ALLOWLIST  # noqa: E402


def _make_package(root: Path, files: dict[str, str]) -> Path:
    """Create a fake ``airunner_services`` tree and return its root."""
    package = root / "services" / "src" / "airunner_services"
    for rel, content in files.items():
        path = package / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return package


def test_the_real_tree_has_no_unlisted_dead_modules() -> None:
    """The repository passes its own dead-module gate."""
    problems = gate.run_check(repo_root=_PROJECT_ROOT)
    assert problems == [], "\n".join(problems)


def test_allowlist_entries_are_current_and_justified() -> None:
    """Every entry still names a real, still-unreferenced module.

    An entry whose file is gone was fixed by deletion; an entry whose
    module is referenced again was fixed by reuse. Both must be removed
    from the allowlist instead of lingering, and every entry must say
    why it exists with a pointer to the owning issue.
    """
    modules, orphans = gate.raw_orphans()
    stale = []
    for module, justification in ALLOWLIST.items():
        if module not in modules:
            stale.append((module, "module no longer exists"))
        elif module not in orphans:
            stale.append((module, "module is referenced again"))
        if "#2480" not in justification:
            stale.append((module, "justification names no owning issue"))
    assert stale == []


def test_allowlist_has_no_wildcards_or_thresholds() -> None:
    """#2480 forbids wildcard entries and count thresholds."""
    for module in ALLOWLIST:
        assert "*" not in module
        assert module.startswith("airunner_services.")
    assert isinstance(ALLOWLIST, dict)


def test_dead_module_is_reported(tmp_path: Path) -> None:
    """A module nothing references is an orphan."""
    package = _make_package(
        tmp_path,
        {
            "live.py": "VALUE = 1\n",
            "dead.py": "VALUE = 2\n",
            "user.py": "from airunner_services.live import VALUE\n",
        },
    )
    _, orphans = gate.raw_orphans(package, [], [])
    assert "airunner_services.dead" in orphans
    assert "airunner_services.live" not in orphans


def test_function_level_import_counts(tmp_path: Path) -> None:
    """A lazy import inside a function body is still a reference.

    Mirrors test_services_importing_airunner_is_caught: the gate must
    not flag modules that are only imported lazily.
    """
    package = _make_package(
        tmp_path,
        {
            "lazy_dep.py": "VALUE = 1\n",
            "user.py": "def load():\n    import airunner_services.lazy_dep\n",
        },
    )
    _, orphans = gate.raw_orphans(package, [], [])
    assert "airunner_services.lazy_dep" not in orphans


def test_dotted_string_reference_counts(tmp_path: Path) -> None:
    """Registry-style dotted strings (runtime bootstrap) are references."""
    package = _make_package(
        tmp_path,
        {
            "client.py": "def register():\n    return 1\n",
            "bootstrap.py": (
                'MODULE = "airunner_services.client"\n'
                "def build():\n"
                "    return __import__(MODULE)\n"
            ),
        },
    )
    _, orphans = gate.raw_orphans(package, [], [])
    assert "airunner_services.client" not in orphans


def test_console_script_string_counts(tmp_path: Path) -> None:
    """``name=module:attr`` console-script strings are references."""
    package = _make_package(
        tmp_path,
        {
            "daemon.py": "def main():\n    return 0\n",
            "table.py": 'ENTRY = "airunner-daemon=airunner_services.daemon:main"\n',
        },
    )
    _, orphans = gate.raw_orphans(package, [], [])
    assert "airunner_services.daemon" not in orphans


def test_package_all_surface_counts(tmp_path: Path) -> None:
    """``__all__`` short names mark lazy ``__getattr__`` modules live."""
    package = _make_package(
        tmp_path,
        {
            "routes/__init__.py": '__all__ = ["art"]\n',
            "routes/art.py": "VALUE = 1\n",
        },
    )
    _, orphans = gate.raw_orphans(package, [], [])
    assert "airunner_services.routes.art" not in orphans


def test_out_of_package_strings_do_not_count(tmp_path: Path) -> None:
    """Policy data outside the package cannot self-license a module.

    Regression: the gate's own allowlist names every exempted module
    as a string key. If out-of-package literals counted, the allowlist
    would mark its own entries live and the gate would be vacuous.
    """
    package = _make_package(
        tmp_path,
        {"orphan_mod.py": "VALUE = 1\n"},
    )
    policy = tmp_path / "policy"
    policy.mkdir()
    (policy / "allowlist.py").write_text(
        'ALLOWLIST = {"airunner_services.orphan_mod": "reason"}\n',
        encoding="utf-8",
    )
    _, orphans = gate.raw_orphans(package, [policy], [])
    assert orphans == {"airunner_services.orphan_mod"}


def test_docstring_mention_does_not_count(tmp_path: Path) -> None:
    """Documenting a module (``:mod:`` prose) is not loading it."""
    package = _make_package(
        tmp_path,
        {
            "documented.py": "VALUE = 1\n",
            "notes.py": (
                '"""See :mod:`airunner_services.documented` for details."""\n'
            ),
        },
    )
    _, orphans = gate.raw_orphans(package, [], [])
    assert "airunner_services.documented" in orphans


def test_dunder_main_and_excluded_trees_are_not_flagged(
    tmp_path: Path,
) -> None:
    """Entry points, tests, and migrations are never reported."""
    package = _make_package(
        tmp_path,
        {
            "tool/__main__.py": "print('hi')\n",
            "tests/test_probe.py": "VALUE = 1\n",
            "alembic/versions/abc123_first.py": "VALUE = 1\n",
        },
    )
    _, orphans = gate.raw_orphans(package, [], [])
    assert orphans == set()


def test_run_check_reports_paths_and_exit_shape(tmp_path: Path) -> None:
    """End-to-end: a dead module in a repo-shaped tree is reported."""
    repo = tmp_path / "repo"
    _make_package(repo, {"dead.py": "VALUE = 1\n"})
    (repo / "services" / "tests").mkdir(parents=True, exist_ok=True)
    (repo / "scripts").mkdir(parents=True, exist_ok=True)
    problems = gate.run_check(repo_root=repo)
    assert len(problems) == 1
    assert "airunner_services.dead" in problems[0]
    assert "services/src/airunner_services/dead.py" in problems[0]


def test_run_check_rejects_missing_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing package root is a configuration error, not a pass."""
    assert gate.main(["--root", str(tmp_path / "nope")]) == 2
    assert "ERROR" in capsys.readouterr().err
