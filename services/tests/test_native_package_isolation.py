"""Regression tests for issue #2065: native/ build-system isolation.

The native package must build through the standard PEP 517 isolated path
(``pip wheel native/``) without importing ``airunner_common`` at setup time.

Issue #2065 proposed two acceptable fixes; the repo chose the second option
("inline the metadata"): ``native/setup.py`` vendors the build metadata
statically (issue #2038) and ``native/pyproject.toml`` declares a
self-contained ``[build-system]`` that only needs setuptools+wheel from the
index. ``airunner_common`` moved to its own repository and is independently
versioned now (issue #2197,
https://github.com/Capsize-Games/airunner-common), so native/setup.py's
vendored values have no live canonical source to drift-check against
anymore -- they are independently authoritative, same as the
services/native requirement registries and setup-kwargs builders that used
to live in ``package_metadata.py`` (removed for the same reason, since
nothing imported them once every consuming setup.py vendored its own
copy).

These tests pin the acceptance criteria:
- ``native/setup.py`` contains no ``airunner_common`` import.
- ``native/pyproject.toml`` declares a setuptools build backend without
  pulling ``airunner-common`` into the isolated build env (it's on PyPI,
  so a build-system requirement on it would resolve, just defeat the
  point of vendoring the metadata statically in the first place).
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_NATIVE_DIR = _PROJECT_ROOT / "native"
_SETUP_PY = _NATIVE_DIR / "setup.py"
_PYPROJECT_TOML = _NATIVE_DIR / "pyproject.toml"


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
    # The vendored setup.py is the isolation boundary (issue #2065, option
    # 2): even though airunner-common is a real published package now, an
    # isolated build resolving it here would defeat the point of vendoring
    # this package's metadata statically.
    assert not any("airunner-common" in req for req in requires), (
        f"isolated build would try to fetch airunner-common: {requires}"
    )
