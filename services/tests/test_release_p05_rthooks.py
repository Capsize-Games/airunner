"""P05 runtime-hook tests (frozen transformers import scan).

Proves the transformers runtime hook maps frozen ``__init__.pyc``
paths to their collected source directory, leaves real directories
unchanged, has no import-time side effects unfrozen, and repairs the
exact frozen failure against the pinned transformers. CPU-only.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import types
from pathlib import Path

import pytest

from test_release_p05_support import REPO_ROOT

RTHOOK_PATH = (
    REPO_ROOT
    / "packaging"
    / "linux"
    / "pyi-rthooks"
    / "pyi_rth_transformers_frozen.py"
)


def _load_rthook() -> types.ModuleType:
    """Load the runtime hook without frozen side effects."""
    found = importlib.util.spec_from_file_location(
        "pyi_rth_transformers_frozen_probe", RTHOOK_PATH
    )
    assert found is not None and found.loader is not None
    module = importlib.util.module_from_spec(found)
    found.loader.exec_module(module)
    return module


def _record_stub(calls: list[str]) -> types.SimpleNamespace:
    """Return a stub import_utils recording the scanned path."""

    def original(module_path: str) -> str:
        calls.append(module_path)
        return f"scanned:{module_path}"

    return types.SimpleNamespace(
        create_import_structure_from_path=original
    )


def test_resolve_scan_dir_keeps_real_directories(
    tmp_path: Path,
) -> None:
    rthook = _load_rthook()
    assert rthook.resolve_scan_dir(str(tmp_path)) == str(tmp_path)


def test_resolve_scan_dir_maps_file_to_parent(tmp_path: Path) -> None:
    target = tmp_path / "models" / "__init__.py"
    target.parent.mkdir(parents=True)
    target.write_text("# fixture\n", encoding="utf-8")
    rthook = _load_rthook()
    assert rthook.resolve_scan_dir(str(target)) == str(target.parent)


def test_resolve_scan_dir_maps_frozen_pyc_to_parent(
    tmp_path: Path,
) -> None:
    """The frozen __init__.pyc path scans its collected parent dir."""
    frozen_style = tmp_path / "models" / "__init__.pyc"
    frozen_style.parent.mkdir(parents=True)
    assert not frozen_style.exists()
    rthook = _load_rthook()
    assert rthook.resolve_scan_dir(str(frozen_style)) == str(
        frozen_style.parent
    )


def test_patch_delegates_with_remapped_path(tmp_path: Path) -> None:
    target = tmp_path / "models" / "__init__.pyc"
    target.parent.mkdir(parents=True)
    calls: list[str] = []
    rthook = _load_rthook()
    wrapped = rthook.patch_create_import_structure(_record_stub(calls))
    assert wrapped(str(target)) == f"scanned:{target.parent}"
    assert calls == [str(target.parent)]


def test_patch_leaves_directory_paths_alone(tmp_path: Path) -> None:
    calls: list[str] = []
    rthook = _load_rthook()
    wrapped = rthook.patch_create_import_structure(_record_stub(calls))
    assert wrapped(str(tmp_path)) == f"scanned:{tmp_path}"
    assert calls == [str(tmp_path)]


def test_rthook_import_is_side_effect_free_unfrozen() -> None:
    """Importing the hook unfrozen must not import transformers."""
    script = (
        f"import sys; sys.path.insert(0, {str(RTHOOK_PATH.parent)!r}); "
        "import pyi_rth_transformers_frozen; "
        "assert not getattr(sys, 'frozen', False); "
        "assert 'transformers' not in sys.modules"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_patch_repairs_frozen_models_scan() -> None:
    """The frozen .pyc path scans once patched (pinned transformers)."""
    pytest.importorskip("transformers")
    from transformers.utils import import_utils

    models_dir = Path(import_utils.__file__).parent.parent / "models"
    frozen_style = str(models_dir / "__init__.pyc")
    assert not Path(frozen_style).exists()
    original = import_utils.create_import_structure_from_path
    with pytest.raises(FileNotFoundError):
        import_utils.define_import_structure(frozen_style)
    rthook = _load_rthook()
    rthook.patch_create_import_structure(import_utils)
    try:
        structure = import_utils.define_import_structure(frozen_style)
    finally:
        import_utils.create_import_structure_from_path = original
    assert "auto.configuration_auto" in structure[frozenset()]
