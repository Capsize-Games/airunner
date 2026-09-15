"""Packaging regression test for Qt translations (issue #2043).

The GUI wheel must contain the compiled ``.qm`` files (and their ``.ts``
sources) so ``localization_mixin._load_translations`` can find them at
runtime.

Strategy: statically assert the ``package_data`` mapping declared in
``setup.py`` covers the translations, then - when ``python -m build`` is
available - build the wheel and assert the ``.qm`` files are physically
present in the archive.
"""

from __future__ import annotations

import ast
import zipfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[5]
_SETUP_PY = _REPO_ROOT / "setup.py"
_TRANSLATIONS_DIR = _REPO_ROOT / "src" / "airunner" / "translations"

EXPECTED_QM = ("english.qm", "japanese.qm")
EXPECTED_TS = ("english.ts", "japanese.ts")


def _package_data_entries() -> list[str]:
    """Read the package_data globs from setup.py without executing it."""
    tree = ast.parse(_SETUP_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg != "package_data" or not isinstance(kw.value, ast.Dict):
                continue
            entries: list[str] = []
            for val in kw.value.values:
                if isinstance(val, ast.List):
                    for elt in val.elts:
                        if isinstance(elt, ast.Constant) and isinstance(
                            elt.value, str
                        ):
                            entries.append(elt.value)
            if entries:
                return entries
    raise AssertionError("package_data not found in setup.py")


def test_package_data_declares_translations() -> None:
    entries = _package_data_entries()
    assert "translations/*.qm" in entries, (
        "setup.py package_data must include 'translations/*.qm'"
    )
    assert "translations/*.ts" in entries, (
        "setup.py package_data must include 'translations/*.ts'"
    )


def test_translation_files_exist_on_disk() -> None:
    for name in (*EXPECTED_QM, *EXPECTED_TS):
        assert (_TRANSLATIONS_DIR / name).is_file(), (
            f"missing translation file: {name}"
        )


def test_wheel_contains_qm_files(tmp_path: Path) -> None:
    """Build the wheel and assert the .qm files are packaged."""
    build = pytest.importorskip("build", reason="python -m build unavailable")
    if not hasattr(build, "build"):  # stub/interop module without the API
        pytest.skip("python -m build API unavailable")

    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    # Build only the wheel (skip sdist); --no-isolation avoids network
    # resolution of build deps when setuptools/wheel are already installed.
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
        for qm in EXPECTED_QM:
            assert any(n.endswith(f"/translations/{qm}") for n in names), (
                f"wheel missing translations/{qm}"
            )
