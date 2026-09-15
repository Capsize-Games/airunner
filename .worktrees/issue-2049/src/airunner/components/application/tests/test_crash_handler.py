"""Tests for the launcher crash capture helpers."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import airunner

_SRC_ROOT = Path(airunner.__file__).resolve().parent.parent
_NATIVE_SRC_ROOT = _SRC_ROOT.parent / "native" / "src"


def _subprocess_env(tmp_path: Path) -> dict[str, str]:
    """Return an environment that points at this worktree's source."""
    env = os.environ.copy()
    env["AIRUNNER_DISABLE_CRASH_DIALOG"] = "1"
    env["QT_QPA_PLATFORM"] = "offscreen"
    existing = env.get("PYTHONPATH", "")
    paths = [str(_SRC_ROOT), str(_NATIVE_SRC_ROOT)]
    env["PYTHONPATH"] = os.pathsep.join(paths) + (
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


def test_gui_exception_handler_forwards_to_gui_log(
    tmp_path: Path,
) -> None:
    """The GUI exception handler (which replaces sys.excepthook during
    startup) still forwards the full traceback to gui.log.

    Reproduces the audit scenario where UIRuntimeMixin.start() installs
    its own sys.excepthook after the launcher's crash handler: the P4
    silent-crash case must still produce an on-disk log.
    """
    script = (
        "import sys\n"
        "from airunner.crash_handler import install_crash_handlers\n"
        "from airunner.app_mixins.ui_runtime_mixin import UIRuntimeMixin\n"
        "install_crash_handlers(log_dir=sys.argv[1])\n"
        "hook = UIRuntimeMixin().exception_handler\n"
        "def raise_in_app():\n"
        "    raise RuntimeError('app-path-77')\n"
        "try:\n"
        "    raise_in_app()\n"
        "except RuntimeError:\n"
        "    hook(*sys.exc_info())\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        env=_subprocess_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0

    log_path = tmp_path / "gui.log"
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "Traceback (most recent call last)" in content
    assert "RuntimeError: app-path-77" in content


def test_reinstall_after_hook_overwrite_rearms_capture(
    tmp_path: Path,
) -> None:
    """Re-installing the crash handlers after sys.excepthook was replaced
    re-arms the on-disk capture (what UIRuntimeMixin.start() now does)."""
    script = (
        "import sys\n"
        "import traceback\n"
        "from airunner.crash_handler import install_crash_handlers\n"
        "install_crash_handlers(log_dir=sys.argv[1])\n"
        "def gui_exception_handler(exctype, value, tb):\n"
        "    traceback.print_exception(exctype, value, tb)\n"
        "    sys.exit(1)\n"
        "sys.excepthook = gui_exception_handler\n"
        "install_crash_handlers(log_dir=sys.argv[1])\n"
        "def boom():\n"
        "    raise RuntimeError('rearm-test-42')\n"
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
    assert "RuntimeError: rearm-test-42" in content


def test_faulthandler_dump_lands_in_log_after_bare_reenable(
    tmp_path: Path,
) -> None:
    """Native faults reach faulthandler.log even after a bare
    faulthandler.enable() (which airunner.main used to call) resets the
    output stream: the fix re-points faulthandler at the on-disk log."""
    script = (
        "import faulthandler\n"
        "import os\n"
        "import signal\n"
        "import sys\n"
        "from airunner.crash_handler import install_crash_handlers\n"
        "install_crash_handlers(log_dir=sys.argv[1])\n"
        "faulthandler.enable()\n"
        "from airunner.crash_handler import install_faulthandler\n"
        "install_faulthandler(log_dir=sys.argv[1])\n"
        "os.kill(os.getpid(), signal.SIGSEGV)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        env=_subprocess_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0

    fault_log_path = tmp_path / "faulthandler.log"
    assert fault_log_path.exists()
    content = fault_log_path.read_text(encoding="utf-8")
    assert "Fatal Python error" in content
    assert (
        "SIGSEGV" in content or "Segmentation fault" in content
    )


def test_native_crash_handler_appends_to_gui_log(
    tmp_path: Path,
) -> None:
    """The native launcher crash handler also lands tracebacks in gui.log."""
    script = (
        "import sys\n"
        "from airunner_native.crash_handler import install_crash_handlers\n"
        "install_crash_handlers(log_dir=sys.argv[1])\n"
        "def boom():\n"
        "    raise RuntimeError('native-crash-42')\n"
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
    assert "RuntimeError: native-crash-42" in content
