"""P05 native-binary and module-hook tests.

Proves the spec's collect_binaries and additional_hooks_dirs keys
reach the freeze command, a missing hooks dir fails the recipe, the
hook files collect the path-loaded .so payloads plus triton-jit
sources, and the inspector fails bundles lacking them. CPU-only.
"""

from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from test_release_p05_support import (
    REPO_ROOT,
    SCRIPTS_DIR,
    SPEC_PATH,
    assemble_mod,
    inspect_mod,
    make_bundle,
    spec,
)

__all__ = ["assemble_mod", "inspect_mod", "spec"]

NATIVE_PACKAGES = frozenset({"mslk", "llama_cpp", "torchcodec"})
FP8_MARKER = "_internal/mslk/quantize/triton/fp8_quantize.py"

_recorded: list[tuple[str, Any]] = []


def _fake_collect(package: str, search_patterns: Any = None) -> list:
    """Record one collect_dynamic_libs call; return no binaries."""
    _recorded.append((package, search_patterns))
    return []


def _exec_hook(path: Path) -> dict[str, Any]:
    """Exec one hook file with stubbed hookutils; return globals."""
    _recorded.clear()
    stub = types.ModuleType("stub_hooks")
    setattr(stub, "collect_dynamic_libs", _fake_collect)
    patched = {
        "PyInstaller": types.ModuleType("PyInstaller"),
        "PyInstaller.utils": types.ModuleType("PyInstaller.utils"),
        "PyInstaller.utils.hooks": stub,
    }
    namespace: dict[str, Any] = {}
    with mock.patch.dict(sys.modules, patched):
        code = path.read_text(encoding="utf-8")
        exec(compile(code, str(path), "exec"), namespace)
    return namespace


def _hooks_dir(spec: dict[str, Any]) -> Path:
    """Return the first declared additional hooks dir."""
    entry = str(spec["code"]["additional_hooks_dirs"][0])
    return REPO_ROOT / entry


def _dry_run_argv(tmp_path: Path) -> list[str]:
    """Return the assembler --dry-run argv for isolated paths."""
    return [
        sys.executable,
        str(SCRIPTS_DIR / "assemble_linux_bundle.py"),
        "--spec",
        str(SPEC_PATH),
        "--distpath",
        str(tmp_path / "dist"),
        "--workpath",
        str(tmp_path / "work"),
        "--base",
        "dryrev",
        "--dry-run",
    ]


def _dry_run_stdout(tmp_path: Path) -> str:
    """Run the assembler --dry-run; return its stdout."""
    proc = subprocess.run(
        _dry_run_argv(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout


def test_spec_collect_binaries_pins_native_packages(
    spec: dict[str, Any],
) -> None:
    """The spec names exactly the path-loaded native packages."""
    assert set(spec["code"].get("collect_binaries", [])) == set(
        NATIVE_PACKAGES
    )


def test_spec_declares_fp8_source_marker(spec: dict[str, Any]) -> None:
    """The triton-jit source marker is a frozen precondition."""
    assert FP8_MARKER in spec["code"].get("frozen_source_markers", [])


def test_hooks_dirs_exist_on_disk(spec: dict[str, Any]) -> None:
    """Every declared hooks dir resolves to a checkout directory."""
    entries = spec["code"].get("additional_hooks_dirs", [])
    assert entries, "spec declares no hooks dirs"
    for entry in entries:
        assert (REPO_ROOT / str(entry)).is_dir(), entry


def test_hook_files_exist(spec: dict[str, Any]) -> None:
    """The mslk and llama_cpp hooks ship in the hooks dir."""
    hooks = _hooks_dir(spec)
    assert (hooks / "hook-mslk.py").is_file()
    assert (hooks / "hook-llama_cpp.py").is_file()


def test_hook_mslk_collects_native_library(
    spec: dict[str, Any],
) -> None:
    """hook-mslk collects the bare mslk.so the default misses."""
    _exec_hook(_hooks_dir(spec) / "hook-mslk.py")
    assert ("mslk", ["*.so"]) in _recorded


def test_hook_mslk_sets_fp8_py_mode(spec: dict[str, Any]) -> None:
    """hook-mslk keeps the triton-jit module as importable source."""
    namespace = _exec_hook(_hooks_dir(spec) / "hook-mslk.py")
    modes = namespace.get("module_collection_mode", {})
    assert modes.get("mslk.quantize.triton.fp8_quantize") == "py"


def test_hook_llama_collects_versioned_libs(
    spec: dict[str, Any],
) -> None:
    """hook-llama_cpp collects the versioned SONAME deps too."""
    _exec_hook(_hooks_dir(spec) / "hook-llama_cpp.py")
    assert _recorded, "hook collects no binaries"
    for package, patterns in _recorded:
        assert package == "llama_cpp"
        assert "*.so" in patterns
        assert "*.so.*" in patterns


def test_build_command_emits_binary_and_hook_flags(
    tmp_path: Path,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    """The freeze recipe collects binaries and hook dirs."""
    command = assemble_mod.build_command(
        spec,
        REPO_ROOT,
        tmp_path / "entry.py",
        tmp_path / "dist",
        tmp_path / "work",
        "pyinstaller",
    )
    text = " ".join(command)
    for package in sorted(NATIVE_PACKAGES):
        assert f"--collect-binaries {package}" in text
    assert "--additional-hooks-dir" in text
    assert "pyi-hooks" in text


def test_build_command_rejects_missing_hooks_dir(
    tmp_path: Path,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    """A declared-but-absent hooks dir fails the freeze recipe."""
    bad = dict(spec)
    bad["code"] = dict(spec["code"], additional_hooks_dirs=["no/such"])
    with pytest.raises(SystemExit, match="hooks dir"):
        assemble_mod.build_command(
            bad,
            REPO_ROOT,
            tmp_path / "entry.py",
            tmp_path / "dist",
            tmp_path / "work",
            "pyinstaller",
        )


def test_dry_run_emits_binary_and_hook_flags(tmp_path: Path) -> None:
    """--dry-run shows the binaries and hooks-dir recipe flags."""
    stdout = _dry_run_stdout(tmp_path)
    for package in sorted(NATIVE_PACKAGES):
        assert f"--collect-binaries {package}" in stdout
    assert "--additional-hooks-dir" in stdout
    assert "pyi-hooks" in stdout


def test_inspect_requires_collected_binaries(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    """A package dir without any .so fails with a clean manifest."""
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    for path in (bundle / "_internal" / "mslk").glob("*.so"):
        path.unlink()
    assemble_mod.write_manifest(bundle, spec, "testrev")
    result = inspect_mod.inspect_bundle(bundle, spec)
    assert any(
        "collected binaries for mslk" in problem
        for problem in result.problems
    )


def test_inspect_requires_fp8_source(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    """A dropped triton-jit source fails with a clean manifest."""
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    marker = bundle / FP8_MARKER
    assert marker.is_file()
    marker.unlink()
    assemble_mod.write_manifest(bundle, spec, "testrev")
    result = inspect_mod.inspect_bundle(bundle, spec)
    assert any("import-scan source" in p for p in result.problems)
