"""P05 assembler dry-run CLI tests.

Proves scripts/assemble_linux_bundle.py resolves every data glob and
prints the exact freeze command under --dry-run without executing
anything, including from an unrelated cwd with PYTHONPATH scrubbed.
CPU-only; no bundle is written.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from test_release_p05_support import SCRIPTS_DIR, SPEC_PATH, scrubbed_env


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


def _dry_run_proc(
    tmp_path: Path, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the assembler --dry-run; return the finished process."""
    return subprocess.run(
        _dry_run_argv(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(tmp_path),
        env=extra_env,
    )


def _assert_recipe_flags(stdout: str) -> None:
    """Assert the freeze recipe flags appear in dry-run output."""
    hidden = "--hidden-import airunner_services.bin.airunner_service"
    for needle in (
        "--onedir",
        "--name",
        "airunner-daemon",
        "--hidden-import airunner_services.llm.tools",
        hidden,
        "--hidden-import libzim",
        "--exclude-module airunner",
        "--exclude-module PySide6",
        "--exclude-module shiboken6",
        "--collect-submodules airunner_services.runtimes",
        "--copy-metadata airunner-services",
        "--add-data",
        "alembic.ini",
    ):
        assert needle in stdout, needle


def test_assemble_dry_run_prints_full_recipe(
    tmp_path: Path,
) -> None:
    """--dry-run resolves globs and prints the freeze command only."""
    proc = _dry_run_proc(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    _assert_recipe_flags(proc.stdout)
    # Root-staged payloads (legal/) are copied post-freeze, never
    # passed as --add-data.
    assert "legal" not in proc.stdout
    assert not (tmp_path / "dist").exists()
    assert not (tmp_path / "work").exists()


def test_assemble_dry_run_without_repo_pythonpath(
    tmp_path: Path,
) -> None:
    """Dry-run works from an unrelated cwd with PYTHONPATH scrubbed."""
    proc = _dry_run_proc(tmp_path, extra_env=scrubbed_env())
    assert proc.returncode == 0, proc.stdout + proc.stderr
