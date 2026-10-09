"""P05 freeze-supply tests (excludes, prune, extensions).

Proves every console module is the freeze entry or an explicit
hidden import, no module-scope import in services/ or native/ can
require an excluded top level, prune entries stay under _internal/
and delete exactly their matches, extension modules are pinned
requirements, and the exclusion allowlist holds exact paths only.
CPU-only.
"""

from __future__ import annotations

import ast
import re
import types
from pathlib import Path
from typing import Any

from test_release_p05_support import (
    REPO_ROOT,
    SERVICES_SETUP,
    assemble_mod,
    inspect_mod,
    spec,
)

__all__ = ["assemble_mod", "inspect_mod", "spec"]

_FREEZE_INPUTS = ("services/src", "native/src")


def _handler_names(node: ast.expr | None) -> set[str]:
    """Return the exception names one handler catches."""
    if node is None:
        return {"*"}
    if isinstance(node, ast.Tuple):
        names: set[str] = set()
        for element in node.elts:
            names |= _handler_names(element)
        return names
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.Attribute):
        return {node.attr}
    return set()


def _guarded(node: ast.Try) -> bool:
    """True when the try/except tolerates import failure."""
    caught: set[str] = set()
    for handler in node.handlers:
        caught |= _handler_names(handler.type)
    return bool(caught & {"*", "Exception", "ImportError"})


def _is_type_checking(node: ast.If) -> bool:
    """True for `if TYPE_CHECKING:` in direct or module form."""
    test = node.test
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    return isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"


def _top_of(module: str) -> str:
    """Return the top-level package of one import target."""
    return module.split(".")[0]


def _statement_tops(node: ast.stmt, tops: set[str]) -> None:
    """Collect unguarded module-scope import tops from one stmt."""
    if isinstance(node, ast.Import):
        tops.update(_top_of(a.name) for a in node.names)
    elif isinstance(node, ast.ImportFrom):
        if node.level == 0 and node.module is not None:
            tops.add(_top_of(node.module))
    elif isinstance(node, ast.If) and not _is_type_checking(node):
        for child in (*node.body, *node.orelse):
            _statement_tops(child, tops)
    elif isinstance(node, ast.Try) and not _guarded(node):
        for child in (*node.body, *node.orelse, *node.finalbody):
            _statement_tops(child, tops)


def _module_scope_tops(path: Path) -> set[str]:
    """Return unguarded module-scope import tops for one file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tops: set[str] = set()
    for node in tree.body:
        _statement_tops(node, tops)
    return tops


def _freeze_sources() -> list[Path]:
    """Return non-test sources feeding the freeze analysis."""
    sources: list[Path] = []
    for stem in _FREEZE_INPUTS:
        for path in sorted((REPO_ROOT / stem).rglob("*.py")):
            if "tests" in path.parts or path.name.startswith("test_"):
                continue
            sources.append(path)
    return sources


def test_console_modules_are_entry_or_hidden(
    spec: dict[str, Any],
) -> None:
    """Every console module is the entry or an explicit hidden import.

    Would have failed before issue #2244: the four non-entry
    console modules were absent from the frozen bundle.
    """
    entry = str(spec["bundle"]["entry_module"])
    hidden = set(spec["code"].get("hidden_imports", []))
    for script in spec.get("console_script", []):
        module = str(script["module"])
        assert module == entry or module in hidden, module


def test_excluded_tops_have_no_module_scope_imports(
    spec: dict[str, Any],
) -> None:
    """No freeze input requires an excluded top level at import.

    TYPE_CHECKING blocks never execute and ImportError-guarded
    try/except blocks degrade; anything else importing airunner,
    PySide6, or shiboken6 at module scope would break the frozen
    daemon, so it fails here instead.
    """
    excluded = set(spec["code"].get("exclude_modules", []))
    assert excluded >= {"airunner", "PySide6", "shiboken6"}
    sources = _freeze_sources()
    assert len(sources) > 500
    for path in sources:
        leaked = _module_scope_tops(path) & excluded
        assert not leaked, (path.relative_to(REPO_ROOT), leaked)


def test_excluded_tops_stay_out_of_warn_allowlist(
    spec: dict[str, Any],
) -> None:
    """Excluded tops must never be declared tolerated-missing.

    An excluded module reported missing (rather than excluded)
    means the exclusion silently failed; allowlisting it would
    hide that regression from the toc-exclusion gate instead.
    """
    allowed = {
        str(name).split(".")[0] for name in spec["warn_allowlist"]["modules"]
    }
    excluded = set(spec["code"].get("exclude_modules", []))
    assert not (allowed & excluded)


def test_prune_globs_stay_under_internal(spec: dict[str, Any]) -> None:
    """Prune entries name _internal/ data with a review reason."""
    entries = spec.get("prune", [])
    assert entries
    for entry in entries:
        assert str(entry["glob"]).startswith("_internal/")
        assert str(entry["reason"]).strip()


def test_exclusion_allowlist_paths_are_exact(
    spec: dict[str, Any],
) -> None:
    """Allowlist paths are exact _internal/ paths, never globs."""
    paths = spec["exclusion_allowlist"]["paths"]
    assert paths
    for path in paths:
        text = str(path)
        assert text.startswith("_internal/")
        assert not any(char in text for char in "*?[]")


def _lock_text(spec: dict[str, Any]) -> str:
    """Return the P02 constraints lock text for the bundle spec."""
    lock_path = REPO_ROOT / str(spec["bundle"]["constraints"])
    return lock_path.read_text(encoding="utf-8")


def test_extension_modules_are_pinned_requirements(
    spec: dict[str, Any],
) -> None:
    """Extension tops are pinned in setup.py or the P02 lock.

    Dotted entries name a submodule .so; the pin applies to the
    top-level distribution, which may be transitive (scipy arrives
    via scikit-learn, pinned only in the lock).
    """
    setup_text = SERVICES_SETUP.read_text(encoding="utf-8")
    lock_text = _lock_text(spec)
    names = spec["code"].get("extension_modules", [])
    assert names
    for name in names:
        top = str(name).split(".")[0]
        direct = f'"{top}==' in setup_text
        locked = re.search(rf"^{re.escape(top)}==", lock_text, re.M)
        assert direct or locked, name


def _prune_fixture(root: Path) -> Path:
    """Build a fake bundle tree with prunable and kept files."""
    bundle = root / "bundle"
    jedi = bundle / "_internal" / "jedi" / "third_party"
    jedi.mkdir(parents=True)
    (jedi / "secrets.pyi").write_text("stub", encoding="utf-8")
    testing = bundle / "_internal" / "torch" / "testing"
    testing.mkdir(parents=True)
    (testing / "test_case.py").write_text("x = 1", encoding="utf-8")
    (testing / "keep.py").write_text("x = 1", encoding="utf-8")
    return bundle


def test_prune_bundle_deletes_matches(
    tmp_path: Path, assemble_mod: types.ModuleType
) -> None:
    """Prune removes glob matches (dirs and files), keeps the rest."""
    bundle = _prune_fixture(tmp_path)
    shard = {
        "prune": [
            {"glob": "_internal/jedi/**", "reason": "fixture"},
            {"glob": "_internal/torch/**/test_*.py", "reason": "f"},
        ]
    }
    removed = assemble_mod.prune_bundle(bundle, shard)
    assert not (bundle / "_internal" / "jedi").exists()
    testing = bundle / "_internal" / "torch" / "testing"
    assert not (testing / "test_case.py").exists()
    assert (testing / "keep.py").is_file()
    assert "_internal/torch/testing/test_case.py" in removed
    assert "_internal/torch/testing/keep.py" not in removed


def test_prune_bundle_ignores_absent_globs(
    tmp_path: Path, assemble_mod: types.ModuleType
) -> None:
    """A prune glob matching nothing removes nothing, no error."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    shard = {"prune": [{"glob": "_internal/absent/**", "reason": "f"}]}
    assert assemble_mod.prune_bundle(bundle, shard) == []


def test_prune_bundle_refuses_escape(
    tmp_path: Path, assemble_mod: types.ModuleType
) -> None:
    """A prune match resolving outside the bundle aborts the build."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("precious", encoding="utf-8")
    (bundle / "sneaky").symlink_to(outside)
    shard = {"prune": [{"glob": "sneaky", "reason": "fixture"}]}
    try:
        assemble_mod.prune_bundle(bundle, shard)
    except SystemExit as exc:
        assert "escapes the bundle" in str(exc)
    else:
        raise AssertionError("prune escape did not abort")
    assert outside.is_file()
