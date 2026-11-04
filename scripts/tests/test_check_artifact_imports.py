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

from check_artifact_imports import (
    _module_scope_imports,
    classify_missing_imports,
    collect,
    load_allowlist,
)


class _Metadata:
    def __init__(self, name: str, extras: tuple[str, ...] = ()) -> None:
        self._values = {"Name": name, "Provides-Extra": list(extras)}

    def get(self, key: str, default=None):
        return self._values.get(key, default)

    def get_all(self, key: str):
        value = self._values.get(key)
        return value if isinstance(value, list) else None


class _Distribution:
    def __init__(
        self,
        name: str,
        *,
        extras: tuple[str, ...] = (),
        requires: tuple[str, ...] = (),
    ) -> None:
        self.metadata = _Metadata(name, extras)
        self.requires = list(requires)


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
    # A conditional import at module scope still executes at import time
    # whenever the branch is taken, so it counts.
    assert _imports(
        """
        if True:
            import lxml
        """
    ) == {"lxml"}


def test_ignores_type_checking_import():
    # `if TYPE_CHECKING:` bodies never run outside a type checker.
    # (`typing` itself is stdlib and filtered by collect, not here.)
    assert _imports(
        """
        from typing import TYPE_CHECKING
        if TYPE_CHECKING:
            import lxml
        """
    ) == {"typing"}


def test_reports_try_import_without_import_error_handler():
    # A try without an ImportError handler (try/finally, or an
    # unrelated except) still raises at import time when missing.
    assert _imports(
        """
        try:
            import lxml
        finally:
            pass
        """
    ) == {"lxml"}
    assert _imports(
        """
        try:
            import lxml
        except ValueError:
            pass
        """
    ) == {"lxml"}


def test_collect_skips_stdlib_and_first_party(tmp_path: Path):
    pkg = tmp_path / "airunner_services"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "mod.py").write_text(
        "import os\nimport json\nimport airunner_common\nimport pygments\n"
    )
    found = collect(tmp_path)
    assert "pygments" in found
    for excluded in ("os", "json", "airunner_common"):
        assert excluded not in found


def test_collect_ignores_lookalike_directories(tmp_path: Path):
    # Exact distribution matching: a vendored `airunner_common_copy`
    # directory is not scanned as first-party, and its imports are
    # not attributed to this project.
    pkg = tmp_path / "airunner_common_copy"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "mod.py").write_text("import pygments\n")
    assert collect(tmp_path) == {}


def test_collect_records_every_importing_file(tmp_path: Path):
    pkg = tmp_path / "airunner_services"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for name in ("a.py", "b.py"):
        (pkg / name).write_text("import pygments\n")
    assert len(collect(tmp_path)["pygments"]) == 2


def test_collect_ignores_unparseable_file(tmp_path: Path):
    pkg = tmp_path / "airunner_services"
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


def test_missing_import_declared_only_by_inactive_extra_is_reported_separately():
    distribution = _Distribution(
        "airunner-services",
        extras=("rag",),
        requires=("langchain-core>=1; extra == 'rag'",),
    )
    undeclared, allowed, inactive = classify_missing_imports(
        {"langchain_core": ["airunner_services/llm/agent.py"]},
        {},
        [distribution],
        set(),
    )

    assert undeclared == {}
    assert allowed == {}
    assert inactive == {
        "langchain_core": (
            ["airunner_services/llm/agent.py"],
            ["airunner-services[rag]"],
        )
    }


def test_missing_base_import_still_fails_even_if_also_in_an_extra():
    distribution = _Distribution(
        "airunner-services",
        extras=("llm-native",),
        requires=(
            "torch>=2.0",
            "torch>=2.0; extra == 'llm-native'",
        ),
    )
    undeclared, _allowed, inactive = classify_missing_imports(
        {"torch": ["airunner_services/api/server.py"]},
        {},
        [distribution],
        set(),
    )

    assert undeclared == {"torch": ["airunner_services/api/server.py"]}
    assert inactive == {}


def test_missing_dependency_from_explicitly_active_extra_still_fails():
    distribution = _Distribution(
        "airunner-services",
        extras=("rag",),
        requires=("langchain-core>=1; extra == 'rag'",),
    )
    undeclared, _allowed, inactive = classify_missing_imports(
        {"langchain_core": ["airunner_services/llm/agent.py"]},
        {},
        [distribution],
        {"rag"},
    )

    assert undeclared == {"langchain_core": ["airunner_services/llm/agent.py"]}
    assert inactive == {}


def test_missing_undeclared_import_still_fails():
    undeclared, _allowed, inactive = classify_missing_imports(
        {"unreviewed_module": ["airunner_services/entry.py"]},
        {},
        [_Distribution("airunner-services")],
        set(),
    )

    assert undeclared == {"unreviewed_module": ["airunner_services/entry.py"]}
    assert inactive == {}


def test_known_import_distribution_alias_is_respected():
    distribution = _Distribution(
        "airunner-services",
        extras=("llm-native",),
        requires=("beautifulsoup4>=4.12; extra == 'llm-native'",),
    )
    _undeclared, _allowed, inactive = classify_missing_imports(
        {"bs4": ["airunner_services/llm/document_loader.py"]},
        {},
        [distribution],
        set(),
    )

    assert inactive == {
        "bs4": (
            ["airunner_services/llm/document_loader.py"],
            ["airunner-services[llm-native]"],
        )
    }


def test_lingua_import_uses_declared_detector_extra():
    distribution = _Distribution(
        "airunner-services",
        extras=("llm-native",),
        requires=("lingua-language-detector==2.1.0; extra == 'llm-native'",),
    )
    _undeclared, _allowed, inactive = classify_missing_imports(
        {"lingua": ["airunner_services/utils/text/language_detection.py"]},
        {},
        [distribution],
        set(),
    )

    assert inactive == {
        "lingua": (
            ["airunner_services/utils/text/language_detection.py"],
            ["airunner-services[llm-native]"],
        )
    }
