"""Tests for the functional-test harness's own cleanup.

``started_daemon`` stops its daemon in a ``finally``. That covers a
failing test and an ending suite; it does not cover the test process
being killed, and then the daemon outlives the run. One was found
still listening three days later, and its run directory was one of 225
left behind.

Both fixes are about the case where no Python gets to run again:
``PR_SET_PDEATHSIG`` hands the guarantee to the kernel, and old run
directories are swept by a later run rather than by the one that made
them.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from llm_functional_support import (
    RUN_DIR_RETENTION_SECONDS,
    _die_with_parent,
    _sweep_old_run_dirs,
)
import llm_functional_support as support


def _run_dir(root: Path, name: str, age_seconds: float) -> Path:
    path = root / name
    path.mkdir(parents=True)
    (path / "daemon.log").write_text("x", encoding="utf-8")
    stamp = time.time() - age_seconds
    os.utime(path, (stamp, stamp))
    return path


def test_an_old_run_directory_is_swept(tmp_path, monkeypatch):
    monkeypatch.setattr(support, "FUNCTIONAL_TEST_LOG_ROOT", tmp_path)
    old = _run_dir(tmp_path, "daemon-old", RUN_DIR_RETENTION_SECONDS + 60)
    assert _sweep_old_run_dirs(time.time()) == 1
    assert not old.exists()


def test_a_recent_run_directory_is_kept(tmp_path, monkeypatch):
    """Long enough to read the log of the run that just failed."""
    monkeypatch.setattr(support, "FUNCTIONAL_TEST_LOG_ROOT", tmp_path)
    fresh = _run_dir(tmp_path, "daemon-fresh", 60)
    assert _sweep_old_run_dirs(time.time()) == 0
    assert fresh.exists()


def test_unrelated_directories_are_left_alone(tmp_path, monkeypatch):
    monkeypatch.setattr(support, "FUNCTIONAL_TEST_LOG_ROOT", tmp_path)
    other = _run_dir(tmp_path, "keep-me", RUN_DIR_RETENTION_SECONDS + 60)
    assert _sweep_old_run_dirs(time.time()) == 0
    assert other.exists()


def test_a_loose_file_is_not_treated_as_a_run_directory(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(support, "FUNCTIONAL_TEST_LOG_ROOT", tmp_path)
    stray = tmp_path / "daemon-stray"
    stray.write_text("not a directory", encoding="utf-8")
    assert _sweep_old_run_dirs(time.time()) == 0
    assert stray.exists()


@pytest.mark.skipif(
    not Path("/proc").is_dir(), reason="PR_SET_PDEATHSIG is Linux-only"
)
def test_a_child_dies_when_the_test_process_is_killed(tmp_path):
    """The three-day-old daemon, reproduced and then prevented.

    The parent is SIGKILLed, so it runs no `finally` and no exit hook
    -- exactly the case the old teardown could not cover.
    """
    parent_source = (
        "import subprocess, sys, time\n"
        f"sys.path.insert(0, {str(Path(support.__file__).parent)!r})\n"
        "from llm_functional_support import _die_with_parent\n"
        "child = subprocess.Popen(\n"
        "    [sys.executable, '-c', 'import time; time.sleep(120)'],\n"
        "    preexec_fn=_die_with_parent,\n"
        ")\n"
        "print(child.pid, flush=True)\n"
        "time.sleep(120)\n"
    )
    parent = subprocess.Popen(
        [sys.executable, "-c", parent_source],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        child_pid = int(parent.stdout.readline().strip())
        assert Path(f"/proc/{child_pid}").exists()
        parent.kill()
        parent.wait(timeout=10)
        deadline = time.time() + 10
        while time.time() < deadline:
            if not Path(f"/proc/{child_pid}").exists():
                break
            time.sleep(0.1)
        assert not Path(f"/proc/{child_pid}").exists(), (
            "the child outlived its killed parent"
        )
    finally:
        parent.kill()


def test_setting_pdeathsig_never_raises(monkeypatch):
    """Best-effort: on a platform without it, the `finally` remains the
    only cleanup and behaviour is exactly as it was."""
    monkeypatch.setattr(
        "ctypes.CDLL", lambda *a, **k: (_ for _ in ()).throw(OSError("no"))
    )
    assert _die_with_parent() is None
