"""Tests for the Try/If-aware module-scope checks (audit wave 2).

Pins the holes closed in scripts/import_boundary_rules.py: module-level
``try``/``if`` imports count as module scope, ``if TYPE_CHECKING:``
does not, unparsable files fail the gate instead of crashing it, and
relative imports never cross the top-level-package boundary.
"""

from __future__ import annotations

import ast
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from check_import_boundaries import (  # noqa: E402
    _allowlist_drift_note,
    _is_allowlisted,
)
from import_boundary_allowlist import ALLOWLIST  # noqa: E402
from import_boundary_rules import (  # noqa: E402
    Violation,
    check_pyside6_not_at_module_scope,
    imported_top_level_names,
)


def _names(source: str) -> set[str]:
    tree = ast.parse(textwrap.dedent(source))
    return {module for _, module in imported_top_level_names(tree)}


def test_relative_imports_never_cross_the_boundary() -> None:
    assert _names("from . import sibling") == set()
    assert _names("from .sub import thing") == set()
    assert _names("from . import airunner") == set()


def test_absolute_cross_package_import_still_counts() -> None:
    assert "airunner.enums" in _names("import airunner.enums")


def test_try_import_at_module_scope_counts(tmp_path: Path) -> None:
    services = tmp_path / "services" / "src" / "airunner_services"
    services.mkdir(parents=True)
    (services / "widget.py").write_text(
        "try:\n    import PySide6.QtWidgets\n"
        "except ImportError:\n    pass\n"
    )
    problems = check_pyside6_not_at_module_scope(tmp_path)
    assert len(problems) == 1
    assert "PySide6" in str(problems[0])


def test_conditional_import_at_module_scope_counts(tmp_path: Path) -> None:
    services = tmp_path / "services" / "src" / "airunner_services"
    services.mkdir(parents=True)
    (services / "widget.py").write_text(
        "import sys\nif sys.version_info >= (3, 11):\n"
        "    import PySide6.QtWidgets\n"
    )
    problems = check_pyside6_not_at_module_scope(tmp_path)
    assert len(problems) == 1


def test_type_checking_import_does_not_count(tmp_path: Path) -> None:
    services = tmp_path / "services" / "src" / "airunner_services"
    services.mkdir(parents=True)
    (services / "widget.py").write_text(
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n    import PySide6.QtWidgets\n"
    )
    assert check_pyside6_not_at_module_scope(tmp_path) == []


def test_unparsable_file_is_a_violation_not_a_crash(
    tmp_path: Path,
) -> None:
    services = tmp_path / "services" / "src" / "airunner_services"
    services.mkdir(parents=True)
    (services / "broken.py").write_text("def (:\n")
    problems = check_pyside6_not_at_module_scope(tmp_path)
    assert len(problems) == 1
    assert problems[0].rule == "syntax-error"


def test_allowlist_drift_note_names_expected_lines() -> None:
    assert ALLOWLIST, "allowlist must be non-empty for this test"
    rel_path, line, imported = sorted(ALLOWLIST)[0]
    drifted = Violation(Path(rel_path), line + 1000, imported, "rule")
    assert not _is_allowlisted(drifted)
    note = _allowlist_drift_note(drifted)
    assert note is not None
    assert str(line) in note

    unrelated = Violation(Path(rel_path), 1, "no.such.module", "rule")
    assert _allowlist_drift_note(unrelated) is None
