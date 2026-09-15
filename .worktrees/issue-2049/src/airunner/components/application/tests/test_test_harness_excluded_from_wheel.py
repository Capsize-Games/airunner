"""Packaging regression test for test-harness exclusion (issue #2046).

The GUI wheel must not ship the developer test harness: ``conftest.py``,
``test_support/`` or any ``*.tests`` packages. This mirrors the
``test_translations_packaged.py`` pattern (issue #2043).

Strategy: statically assert ``setup.py`` (a) excludes the harness from
``find_packages`` and ``exclude_package_data`` and (b) has no stale
``package_data`` globs, then - when ``python -m build`` is available - build
the wheel and assert none of the harness paths are present in the archive.
"""

from __future__ import annotations

import ast
import zipfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[5]
_SETUP_PY = _REPO_ROOT / "setup.py"

STALE_PACKAGE_DATA_GLOBS = (
    "components/icons/*",
    "components/art/filters/*",
)
EXPECTED_PACKAGE_DATA_GLOBS = (
    "gui/cursors/*",
    "gui/images/*",
    "gui/resources/**/*",
    "gui/styles/**/*",
    "components/**/templates/*.ui",
    "components/**/user_agreement/*.md",
    "components/**/static/**/*",
    "static/**/*",
    "translations/*.qm",
    "translations/*.ts",
)
EXCLUDED_PACKAGE_NAMES = (
    "airunner.conftest",
    "airunner.test_support",
    "*.tests",
    "*.tests.*",
)


def _find_call(tree: ast.AST, func_name: str) -> ast.Call:
    """Return the first Call node to ``func_name`` in an AST."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == func_name:
            return node
    raise AssertionError(f"call to {func_name}() not found in setup.py")


def _keyword_value(call: ast.Call, name: str) -> ast.AST:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    raise AssertionError(f"keyword {name!r} not found in setup.py call")


def _literal_strings(node: ast.AST) -> list[str]:
    """Collect all string literals from an AST node."""
    values: list[str] = []
    for elt in ast.walk(node):
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
            values.append(elt.value)
    return values


def _package_data_entries() -> list[str]:
    """Read the package_data globs from setup.py without executing it."""
    tree = ast.parse(_SETUP_PY.read_text(encoding="utf-8"))
    return _literal_strings(_keyword_value(_find_call(tree, "setup"), "package_data"))


def _find_packages_excludes() -> list[str]:
    """Read the find_packages(...) exclude list from setup.py."""
    tree = ast.parse(_SETUP_PY.read_text(encoding="utf-8"))
    call = _find_call(tree, "find_packages")
    try:
        excludes = _keyword_value(call, "exclude")
    except AssertionError:
        return []
    return _literal_strings(excludes)


def _exclude_package_data_entries() -> list[str]:
    """Read the exclude_package_data globs from setup.py."""
    tree = ast.parse(_SETUP_PY.read_text(encoding="utf-8"))
    try:
        mapping = _keyword_value(_find_call(tree, "setup"), "exclude_package_data")
    except AssertionError:
        return []
    return _literal_strings(mapping)


def test_find_packages_excludes_test_harness() -> None:
    excludes = _find_packages_excludes()
    for name in EXCLUDED_PACKAGE_NAMES:
        assert name in excludes, (
            f"find_packages exclude must contain {name!r} (got {excludes})"
        )


def test_exclude_package_data_covers_conftest() -> None:
    entries = _exclude_package_data_entries()
    assert "conftest.py" in entries, (
        "exclude_package_data must exclude 'conftest.py' from the wheel"
    )
    assert any(e.startswith("test_support") for e in entries), (
        "exclude_package_data must cover test_support/ paths"
    )


def test_package_data_has_no_stale_globs() -> None:
    entries = _package_data_entries()
    for glob in STALE_PACKAGE_DATA_GLOBS:
        assert glob not in entries, (
            f"package_data must not contain stale glob {glob!r}"
        )
    for glob in EXPECTED_PACKAGE_DATA_GLOBS:
        assert glob in entries, (
            f"package_data must retain glob {glob!r} (got {entries})"
        )


def test_wheel_contains_no_test_harness(tmp_path: Path) -> None:
    """Build the wheel and assert the test harness is not packaged."""
    build = pytest.importorskip("build", reason="python -m build unavailable")
    if not hasattr(build, "build"):  # stub/interop module without the API
        pytest.skip("python -m build API unavailable")

    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    try:
        build.build(
            srcdir=str(_REPO_ROOT),
            outdir=str(dist_dir),
            distribution="wheel",
            isolation=False,
        )
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"wheel build failed in this environment: {exc}")

    wheels = list(dist_dir.glob("*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, got {wheels}"
    with zipfile.ZipFile(wheels[0]) as zf:
        names = set(zf.namelist())
        forbidden = [
            n
            for n in names
            if n.endswith("/conftest.py")
            or "/test_support/" in n
            or "/tests/" in n
        ]
        assert not forbidden, (
            f"wheel contains test harness paths: {sorted(forbidden)}"
        )
