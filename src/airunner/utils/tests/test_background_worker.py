"""
Unit tests for airunner.utils.application.background_worker.BackgroundWorker
"""

import pytest
from unittest.mock import MagicMock
import time
import types
import sys
import importlib
import builtins


@pytest.fixture(autouse=True)
def patch_qt_signals(monkeypatch):
    # Patch PySide6.QtCore.Signal and QThread only for this module's import
    import sys
    import types

    orig_qtcore = sys.modules.get("PySide6.QtCore")
    fake_signal = lambda *a, **k: MagicMock()
    fake_qtcore = types.SimpleNamespace(QThread=object, Signal=fake_signal)
    sys.modules["PySide6.QtCore"] = fake_qtcore
    yield
    # Restore original module if it existed, else remove
    if orig_qtcore is not None:
        sys.modules["PySide6.QtCore"] = orig_qtcore
    else:
        del sys.modules["PySide6.QtCore"]


def test_worker_runs_and_emits(monkeypatch, patch_qt_signals):
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
    # Patch the emit methods of the class attributes
    worker.progressUpdate.emit = MagicMock()
    worker.statusUpdate.emit = MagicMock()
    worker.taskFinished.emit = MagicMock()
    worker.run()
    assert called["ran"]
    worker.progressUpdate.emit.assert_called_with(42)
    worker.statusUpdate.emit.assert_called_with("working")
    worker.taskFinished.emit.assert_called()
    data = worker.taskFinished.emit.call_args[0][0]
    assert data["result"] == 123
    assert data["duration"] == 0.0
    assert data["cancelled"] is False


def test_worker_cancel_property(monkeypatch, patch_qt_signals):
    import airunner.utils.application.background_worker as bgworker_mod

    importlib.reload(bgworker_mod)
    BackgroundWorker = bgworker_mod.BackgroundWorker
    worker = BackgroundWorker()
    assert not worker.is_cancelled
    worker.cancel()
    assert worker.is_cancelled


def test_worker_error(monkeypatch, patch_qt_signals):
    monkeypatch.setattr(time, "time", lambda: 100.0)
    import airunner.utils.application.background_worker as bgworker_mod

    importlib.reload(bgworker_mod)
    BackgroundWorker = bgworker_mod.BackgroundWorker

    def bad_task(worker):
        raise ValueError("fail!")

    worker = BackgroundWorker(task_function=bad_task)
    worker.taskFinished.emit = MagicMock()
    worker.run()
    worker.taskFinished.emit.assert_called()
    data = worker.taskFinished.emit.call_args[0][0]
    assert "error" in data
    assert "fail!" in data["error"]
    assert data["cancelled"] is False
    assert data["duration"] == 0.0
