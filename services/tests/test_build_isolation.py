"""Build-system isolation guard for the services package (issue #2064).

``pip wheel services/`` runs in an isolated PEP 517 build environment that only
contains the ``[build-system] requires`` entries. services/setup.py must
therefore never import the shared ``airunner_common`` package (or anything else
not declared there) at setup time, or the build fails with
ModuleNotFoundError. These tests lock that invariant in place.
"""

from __future__ import annotations

import ast
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _imports_setuptools_only(path: Path) -> list[str]:
    """Return the module-level imports (or import-from) of a setup.py file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    return imported


def test_services_setup_py_has_no_module_level_airunner_common_import() -> None:
    """The build metadata is vendored; no shared-package import at setup time."""
    imports = _imports_setuptools_only(_PROJECT_ROOT / "services" / "setup.py")
    assert not any(
        imp == "airunner_common" or imp.startswith("airunner_common.")
        for imp in imports
    ), f"services/setup.py must not import airunner_common at build time, got: {imports}"


def test_native_setup_py_has_no_module_level_airunner_common_import() -> None:
    """native/setup.py follows the same self-contained rule (issue #2038)."""
    imports = _imports_setuptools_only(_PROJECT_ROOT / "native" / "setup.py")
    assert not any(
        imp == "airunner_common" or imp.startswith("airunner_common.")
        for imp in imports
    ), f"native/setup.py must not import airunner_common at build time, got: {imports}"


def test_services_pyproject_declares_build_backend() -> None:
    """services/pyproject.toml must declare a PEP 517 build backend."""
    text = (_PROJECT_ROOT / "services" / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert "[build-system]" in text
    assert "build-backend = \"setuptools.build_meta\"" in text
    assert "setuptools" in text, "setuptools must be in build-system requires"
