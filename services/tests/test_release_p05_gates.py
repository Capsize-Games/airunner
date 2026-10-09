"""P05 freeze-gate, sidecar, policy, and inspect CLI tests.

Proves the warn-file gate, frozen-module checks, sidecar
warn-by-default semantics, the synthetic policy fixture, and the
inspect CLI over scrubbed PYTHONPATH. CPU-only.
"""

from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path
from typing import Any

from test_release_p05_support import (
    SCRIPTS_DIR,
    SPEC_PATH,
    SYNTHETIC_POLICY,
    WARN_CLEAN,
    assemble_mod,
    inspect_mod,
    make_bundle,
    scrubbed_env,
    spec,
    write_toc,
    write_warn,
)

__all__ = ["assemble_mod", "inspect_mod", "spec"]


def test_warn_gate_parses_real_shapes(
    inspect_mod: types.ModuleType,
) -> None:
    """Bare and quoted missing modules parse; excluded lines ignored."""
    missing = inspect_mod.parse_warn_file(WARN_CLEAN)
    assert set(missing) == {
        "winreg",
        "nt",
        "_winapi",
        "msvcrt",
        "_frozen_importlib_external",
        "collections.abc",
    }


def test_warn_gate_rejects_unreviewed_module(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    allowlist = list(spec["warn_allowlist"]["modules"])
    clean = write_warn(tmp_path / "clean.txt", dirty=False)
    problems, tolerated = inspect_mod.gate_warn_file(clean, allowlist)
    assert problems == []
    assert {"winreg", "collections.abc"} <= set(tolerated)
    dirty = write_warn(tmp_path / "dirty.txt", dirty=True)
    problems, _ = inspect_mod.gate_warn_file(dirty, allowlist)
    assert problems == ["unreviewed missing module: no_such_reviewed_module"]


def test_warn_gate_tolerates_excluded_tops(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    """Excluded tops tolerated as missing; toc gate enforces absence."""
    warn = tmp_path / "excluded.txt"
    warn.write_text(
        "missing module named airunner - imported by x (conditional)\n"
        "missing module named 'PySide6.QtCore' - imported by y (top)\n",
        encoding="utf-8",
    )
    excluded = list(spec["code"].get("exclude_modules", []))
    assert {"airunner", "PySide6"} <= set(excluded)
    problems, tolerated = inspect_mod.gate_warn_file(warn, [], excluded)
    assert problems == []
    assert {"airunner", "PySide6.QtCore"} <= set(tolerated)


def test_toc_check_requires_console_modules(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    full = write_toc(tmp_path / "full.toc", spec)
    problems, _ = inspect_mod.check_toc_modules([full], spec)
    assert problems == []
    dropped = write_toc(
        tmp_path / "thin.toc",
        spec,
        drop=frozenset({"airunner_services.daemon"}),
    )
    problems, _ = inspect_mod.check_toc_modules([dropped], spec)
    assert problems == ["frozen bundle lacks module airunner_services.daemon"]


def test_toc_check_rejects_excluded_module(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    """A frozen module under an excluded top level fails the gate."""
    toc = write_toc(tmp_path / "qt.toc", spec)
    with toc.open("a", encoding="utf-8") as handle:
        handle.write("  ('airunner.gui.window', '/x.py', 'PYMODULE'),\n")
        handle.write("  ('PySide6.QtCore', '/y.py', 'PYMODULE'),\n")
    problems, _ = inspect_mod.check_toc_modules([toc], spec)
    assert "frozen bundle ships excluded module PySide6.QtCore" in problems
    assert (
        "frozen bundle ships excluded module airunner.gui.window" in problems
    )


def test_sidecars_warn_by_default_fail_when_required(
    tmp_path: Path,
    inspect_mod: types.ModuleType,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    quiet = inspect_mod.inspect_bundle(bundle, spec)
    assert quiet.problems == []
    assert any("llama-server" in w for w in quiet.warnings)
    strict = inspect_mod.inspect_bundle(bundle, spec, require_sidecars=True)
    assert any("llama-server" in p for p in strict.problems)
    assert any("whisper-server" in p for p in strict.problems)


def test_synthetic_policy_fixture_used(
    tmp_path: Path,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    """The fixture policy payload is synthetic, never production data."""
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    policy = (
        bundle
        / "_internal"
        / "airunner_services"
        / "content_safety"
        / "data"
        / "probe.dat"
    )
    assert policy.read_bytes() == SYNTHETIC_POLICY


def _run_cli(bundle: Path, cwd: Path, expect: int, needle: str) -> None:
    """Run the inspect CLI with PYTHONPATH scrubbed; assert outcome."""
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "inspect_linux_bundle.py"),
            "--spec",
            str(SPEC_PATH),
            str(bundle),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(cwd),
        env=scrubbed_env(),
    )
    assert proc.returncode == expect, proc.stdout + proc.stderr
    assert needle in proc.stdout


def test_inspect_cli_passes_without_repo_pythonpath(
    tmp_path: Path,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    """Acceptance: inspection succeeds with no repository PYTHONPATH."""
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    _run_cli(bundle, tmp_path, 0, "OK:")


def test_inspect_cli_fails_tampered_bundle_without_repo_pythonpath(
    tmp_path: Path,
    assemble_mod: types.ModuleType,
    spec: dict[str, Any],
) -> None:
    bundle = make_bundle(tmp_path, spec, assemble_mod)
    (bundle / "stray.txt").write_text("unmanifested", encoding="utf-8")
    _run_cli(bundle, tmp_path, 1, "FAIL:")
