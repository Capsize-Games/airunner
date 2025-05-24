"""
Unit tests for airunner.utils.application.create_worker.create_worker
"""

import pytest
from unittest.mock import MagicMock
import airunner.utils as utils


def test_create_worker_returns_mock_in_test_mode(monkeypatch):
    monkeypatch.setenv("AIRUNNER_TEST_MODE", "1")
    worker = utils.create_worker(lambda: None)
    assert isinstance(worker, MagicMock)
    monkeypatch.delenv("AIRUNNER_TEST_MODE")


def test_create_worker_real(monkeypatch):
    import sys
    import types
    import importlib

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

        def start(self):
            self.started()

        def quit(self):
            pass

    fake_qtcore = types.SimpleNamespace(QThread=DummyThread)
    sys.modules["PySide6.QtCore"] = fake_qtcore
    monkeypatch.setenv("AIRUNNER_TEST_MODE", "0")
    create_worker_mod = importlib.import_module(
        "airunner.utils.application.create_worker"
    )
    worker = create_worker_mod.create_worker(DummyWorker, foo=1)
    assert isinstance(worker, DummyWorker)
    assert worker.kwargs["foo"] == 1
    monkeypatch.delenv("AIRUNNER_TEST_MODE")
    del sys.modules["PySide6.QtCore"]
