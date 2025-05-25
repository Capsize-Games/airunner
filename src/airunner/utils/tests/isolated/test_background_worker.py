# NOTE: This test file must be run in a real Qt environment (with a display or xvfb),
# and without patching PySide6.QtCore. Do NOT run this file as part of the main suite or in headless mode.
#
# To automate this, you can add the following to your Makefile or CI script (for display environments):
#   xvfb-run -a pytest src/airunner/utils/tests/isolated/test_background_worker.py
#
# Do NOT run this file as part of the main suite or with pytest-qt enabled.

"""
Unit tests for airunner.utils.application.background_worker.BackgroundWorker
"""

import pytest
from unittest.mock import MagicMock
import time
import importlib

# Remove all patching of PySide6.QtCore. These tests require a real Qt environment.


def test_worker_runs_and_emits(monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 100.0)
    import airunner.utils.application.background_worker as bgworker_mod

    importlib.reload(bgworker_mod)
    BackgroundWorker = bgworker_mod.BackgroundWorker
    called = {}

    def task(worker):
        called["ran"] = True
        worker.update_progress(42)
        worker.update_status("working")
        return 123

    worker = BackgroundWorker(task_function=task)
    progress_mock = MagicMock()
    status_mock = MagicMock()
    finished_mock = MagicMock()
    worker.progressUpdate.connect(progress_mock)
    worker.statusUpdate.connect(status_mock)
    worker.taskFinished.connect(finished_mock)
    worker.run()
    # Explicit thread cleanup if needed
    if hasattr(worker, "wait"):
        worker.wait()
    assert called["ran"]
    progress_mock.assert_called_with(42)
    status_mock.assert_called_with("working")
    finished_mock.assert_called()
    data = finished_mock.call_args[0][0]
    assert data["result"] == 123
    assert data["duration"] == 0.0
    assert data["cancelled"] is False


def test_worker_cancel_property():
    import airunner.utils.application.background_worker as bgworker_mod

    importlib.reload(bgworker_mod)
    BackgroundWorker = bgworker_mod.BackgroundWorker
    worker = BackgroundWorker()
    assert not worker.is_cancelled
    worker.cancel()
    # Explicit thread cleanup if needed
    if hasattr(worker, "wait"):
        worker.wait()
    assert worker.is_cancelled


def test_worker_error(monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 100.0)
    import airunner.utils.application.background_worker as bgworker_mod

    importlib.reload(bgworker_mod)
    BackgroundWorker = bgworker_mod.BackgroundWorker

    def bad_task(worker):
        raise ValueError("fail!")

    worker = BackgroundWorker(task_function=bad_task)
    finished_mock = MagicMock()
    worker.taskFinished.connect(finished_mock)
    worker.run()
    # Explicit thread cleanup if needed
    if hasattr(worker, "wait"):
        worker.wait()
    finished_mock.assert_called()
    data = finished_mock.call_args[0][0]
    assert "error" in data
    assert "fail!" in data["error"]
    assert data["cancelled"] is False
    assert data["duration"] == 0.0
