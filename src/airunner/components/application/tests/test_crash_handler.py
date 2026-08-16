"""Tests for the launcher crash capture helpers."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import airunner

_SRC_ROOT = Path(airunner.__file__).resolve().parent.parent


def _subprocess_env(tmp_path: Path) -> dict[str, str]:
    """Return an environment that points at this worktree's source."""
    env = os.environ.copy()
    env["AIRUNNER_DISABLE_CRASH_DIALOG"] = "1"
    env["QT_QPA_PLATFORM"] = "offscreen"
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(_SRC_ROOT) + (
        os.pathsep + existing if existing else ""
    )
    return env


def test_uncaught_exception_appends_traceback_to_gui_log(
    tmp_path: Path,
) -> None:
    """An uncaught exception in the app path lands in gui.log."""
    script = (
        "import sys\n"
        "from airunner.crash_handler import install_crash_handlers\n"
        "install_crash_handlers(log_dir=sys.argv[1])\n"
        "def boom():\n"
        "    raise RuntimeError('crash-test-42')\n"
        "boom()\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        env=_subprocess_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0

    log_path = tmp_path / "gui.log"
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "Traceback (most recent call last)" in content
    assert "RuntimeError: crash-test-42" in content


def test_unraisablehook_appends_background_failure_to_log(
    tmp_path: Path,
) -> None:
    """A background-thread/GC failure lands in gui.log."""
    script = (
        "import gc\n"
        "import sys\n"
        "import time\n"
        "from airunner.crash_handler import install_crash_handlers\n"
        "install_crash_handlers(log_dir=sys.argv[1])\n"
        "class Boom:\n"
        "    def __del__(self):\n"
        "        raise RuntimeError('unraisable-42')\n"
        "obj = Boom()\n"
        "del obj\n"
        "gc.collect()\n"
        "time.sleep(0.2)\n"
    )
    subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        env=_subprocess_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=30,
    )

    log_path = tmp_path / "gui.log"
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "unraisable-42" in content
