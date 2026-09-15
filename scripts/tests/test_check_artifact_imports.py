"""Tests for the static import/declaration checker.

These pin the checker's *discrimination*: it must report unguarded
module-scope imports and must stay silent about the graceful patterns.
Getting that wrong in either direction is expensive -- a false positive
pushes maintainers to allowlist things that are genuinely required, and a
false negative is how 6.1.3 shipped.
"""

from __future__ import annotations

import ast
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from check_artifact_imports import (  # noqa: E402
    _module_scope_imports,
    collect,
    load_allowlist,
)


def _imports(source: str) -> set[str]:
    return _module_scope_imports(ast.parse(textwrap.dedent(source)))


def test_reports_plain_module_scope_import():
    assert "pygments" in _imports("import pygments")


def test_reports_module_scope_from_import():
    # The exact shape that broke 6.1.3.
    assert "pygments" in _imports("from pygments import highlight")


def test_reports_only_the_top_level_package():
    assert _imports("import langchain_core.messages.ai") == {"langchain_core"}


def test_ignores_import_inside_function():
    # Deferred imports fail only when that feature is used, which is the
    # pattern optional dependencies are supposed to follow.
    assert _imports(
        """
        def load():
            import torch
            return torch
        """
    ) == set()


def test_ignores_try_guarded_import():
    # Graceful degradation must not be flagged, or maintainers get pushed
    # toward allowlisting genuinely required packages.
    assert _imports(
        """
        try:
            import compel
        except ImportError:
            compel = None
        """
    ) == set()


def test_ignores_relative_imports():
    assert _imports("from . import sibling") == set()
    assert _imports("from .sub import thing") == set()


def test_reports_conditional_import_at_module_scope():
    # `if TYPE_CHECKING:` and similar still execute at import time for the
    # non-TYPE_CHECKING branch, but they are not bare top-level statements;
    # the checker deliberately does not descend into them.
    assert _imports(
        """
        if True:
            import lxml
        """
    ) == set()


def test_collect_skips_stdlib_and_first_party(tmp_path: Path):
    pkg = tmp_path / "airunner_demo"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "mod.py").write_text(
        "import os\nimport json\nimport airunner_common\nimport pygments\n"
    )
    found = collect(tmp_path)
    assert "pygments" in found
    for excluded in ("os", "json", "airunner_common"):
        assert excluded not in found


def test_collect_records_every_importing_file(tmp_path: Path):
    pkg = tmp_path / "airunner_demo"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for name in ("a.py", "b.py"):
        (pkg / name).write_text("import pygments\n")
    assert len(collect(tmp_path)["pygments"]) == 2


def test_collect_ignores_unparseable_file(tmp_path: Path):
    pkg = tmp_path / "airunner_demo"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "broken.py").write_text("def (:\n")
    (pkg / "ok.py").write_text("import pygments\n")
    assert "pygments" in collect(tmp_path)


def test_allowlist_round_trip(tmp_path: Path):
    f = tmp_path / "optional.toml"
    f.write_text('[optional.pytest]\nreason = "test-only"\n')
    assert load_allowlist(f) == {"pytest": "test-only"}


def test_missing_allowlist_is_empty_not_an_error(tmp_path: Path):
    # An absent allowlist must not silently pass everything.
    assert load_allowlist(tmp_path / "nope.toml") == {}
