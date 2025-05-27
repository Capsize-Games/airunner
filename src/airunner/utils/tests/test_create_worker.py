"""
Unit tests for airunner.utils.application.create_worker.create_worker
"""

import pytest
from unittest.mock import MagicMock
import airunner.utils as utils


def test_create_worker_returns_mock_in_test_mode(monkeypatch):
    monkeypatch.setenv("AIRUNNER_TEST_MODE", "1")
    worker, thread = utils.create_worker(lambda: None)
    from unittest.mock import MagicMock

    assert isinstance(worker, MagicMock)
    assert isinstance(thread, MagicMock)
    monkeypatch.delenv("AIRUNNER_TEST_MODE")


def test_create_worker_real(monkeypatch):
    import sys
    import types
    import importlib
    import importlib.util

    class DummyWorker:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def moveToThread(self, thread):
            self.thread = thread

        def run(self):
            self.ran = True

        finished = MagicMock()

    class DummyThread:
        def __init__(self):
            self.started = MagicMock()
            self.quit_called = False
            self.wait_called = False

        def start(self):
            self.started()

        def quit(self):
            self.quit_called = True

        def wait(self, timeout=None):
            self.wait_called = True

    # Patch PySide6.QtCore.QThread to DummyThread before importing create_worker
    fake_qtcore = types.SimpleNamespace(QThread=DummyThread)
    sys.modules["PySide6.QtCore"] = fake_qtcore
    monkeypatch.setenv("AIRUNNER_TEST_MODE", "0")
    # Reload the module to ensure it uses DummyThread
    importlib.invalidate_caches()
    if "airunner.utils.application.create_worker" in sys.modules:
        del sys.modules["airunner.utils.application.create_worker"]
    create_worker_mod = importlib.import_module(
        "airunner.utils.application.create_worker"
    )
    worker, thread = create_worker_mod.create_worker(DummyWorker, foo=1)
    assert isinstance(worker, DummyWorker)
    assert worker.kwargs["foo"] == 1
    # Ensure thread is properly shut down
    if thread is not None:
        thread.quit()
        thread.wait()
        # Only check attributes if DummyThread
        if isinstance(thread, DummyThread):
            assert thread.quit_called
            assert thread.wait_called
    monkeypatch.delenv("AIRUNNER_TEST_MODE")
    del sys.modules["PySide6.QtCore"]
