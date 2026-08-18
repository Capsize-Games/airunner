"""Regression tests for issue #2065: native/ build-system isolation.

The native package must build through the standard PEP 517 isolated path
(``pip wheel native/``) without importing ``airunner_common`` at setup time.

Issue #2065 proposed two acceptable fixes; the repo chose the second option
("inline the metadata"): ``native/setup.py`` vendors the build metadata
statically (issue #2038) and ``native/pyproject.toml`` declares a
self-contained ``[build-system]`` that only needs setuptools+wheel from the
index. ``airunner-common`` is not published to PyPI, so it must never be
fetched into the isolated build environment.

These tests pin the acceptance criteria:
- ``native/setup.py`` contains no ``airunner_common`` import.
- ``native/pyproject.toml`` declares a setuptools build backend without
  pulling ``airunner-common`` into the isolated build env.
- The vendored metadata still matches
  ``shared/airunner_common/package_metadata.py`` so the surfaces cannot
  drift apart (architecture audit finding O1).
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

from airunner_common import package_metadata

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_NATIVE_DIR = _PROJECT_ROOT / "native"
_SETUP_PY = _NATIVE_DIR / "setup.py"
_PYPROJECT_TOML = _NATIVE_DIR / "pyproject.toml"


def _module_assignments(source: str) -> dict[str, ast.AST]:
    """Return module-level ``name -> value node`` for one setup.py source."""
    tree = ast.parse(source)
    assignments: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments[target.id] = node.value
    return assignments


def _evaluate_node(node: ast.AST, assignments: dict[str, ast.AST]) -> object:
    """Statically evaluate the subset of Python used by the vendored values.

    Supports string constants, string ``f-strings`` (``VERSION``
    interpolation), ``Name`` references and flat string lists — everything
    ``native/setup.py`` uses for its vendored metadata. Anything else fails
    loudly so a metadata edit that outgrows this evaluator is reviewed.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return _evaluate_node(assignments[node.id], assignments)
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                inner = _evaluate_node(value.value, assignments)
                if not isinstance(inner, str):
                    raise AssertionError(
                        "f-string interpolation must resolve to str, "
                        f"got {inner!r}"
                    )
                parts.append(inner)
            else:
                raise AssertionError(
                    f"unsupported JoinedStr value: {ast.dump(value)}"
                )
        return "".join(parts)
    if isinstance(node, ast.List):
        return [_evaluate_node(elt, assignments) for elt in node.elts]
    raise AssertionError(f"unsupported setup.py node: {ast.dump(node)}")


def test_setup_py_has_no_airunner_common_import() -> None:
    """native/setup.py must not import airunner_common at setup time."""
    source = _SETUP_PY.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("airunner_common"), (
                    f"native/setup.py imports {alias.name!r}; build isolation "
                    "for pip wheel native/ would fail"
                )
        elif isinstance(node, ast.ImportFrom):
            assert node.module is None or not node.module.startswith(
                "airunner_common"
            ), (
                f"native/setup.py imports {node.module!r}; build isolation "
                "for pip wheel native/ would fail"
            )

    # Belt-and-braces: no textual import statement either (e.g. a dynamic
    # import built from a string).
    for line in source.splitlines():
        stripped = line.strip()
        assert not stripped.startswith("import airunner_common"), (
            f"native/setup.py contains {stripped!r}"
        )
        assert not stripped.startswith("from airunner_common"), (
            f"native/setup.py contains {stripped!r}"
        )


def test_pyproject_build_system_is_self_contained() -> None:
    """native/pyproject.toml must not fetch airunner-common in isolation."""
    with _PYPROJECT_TOML.open("rb") as handle:
        data = tomllib.load(handle)
    build_system = data["build-system"]

    assert build_system["build-backend"] == "setuptools.build_meta"

    requires = build_system["requires"]
    assert any(req.startswith("setuptools") for req in requires)
    assert "wheel" in requires
    # airunner-common is not published to PyPI; the isolated build env must
    # never try to resolve it. The vendored setup.py is the isolation
    # boundary (issue #2065, option 2).
    assert not any("airunner-common" in req for req in requires), (
        f"isolated build would try to fetch airunner-common: {requires}"
    )


def test_vendored_metadata_matches_package_metadata() -> None:
    """The vendored values in native/setup.py must match the shared source.

    native/setup.py is intentionally static (no build-time airunner_common
    import), so this test is the drift guard that keeps it in sync with
    shared/airunner_common/package_metadata.py.
    """
    assignments = _module_assignments(_SETUP_PY.read_text(encoding="utf-8"))

    assert _evaluate_node(assignments["VERSION"], assignments) == (
        package_metadata.VERSION
    )
    assert _evaluate_node(
        assignments["FACEHUGGERSHIELD_REQUIREMENT"], assignments
    ) == package_metadata.FACEHUGGERSHIELD_REQUIREMENT
    assert _evaluate_node(
        assignments["NATIVE_BASE_REQUIREMENTS"], assignments
    ) == package_metadata.NATIVE_BASE_REQUIREMENTS
    assert _evaluate_node(
        assignments["NATIVE_CONSOLE_SCRIPTS"], assignments
    ) == package_metadata.NATIVE_CONSOLE_SCRIPTS
