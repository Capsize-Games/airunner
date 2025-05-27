"""
Test that all QThreads are properly stopped and joined on application shutdown.
"""

import pytest
from unittest.mock import MagicMock
from airunner.gui.windows.main.worker_manager import WorkerManager


class DummyThread:
    def __init__(self):
        self._running = True
        self.quit_called = False
        self.wait_called = False

    def isRunning(self):
        return self._running

    def quit(self):
        self.quit_called = True
        self._running = False

    def wait(self, timeout=None):
        self.wait_called = True


class DummyWorker:
    def __init__(self):
        self.stopped = False
        self.canceled = False

    def stop(self):
        self.stopped = True

    def cancel(self):
        self.canceled = True


def test_shutdown_workers_stops_and_joins_all():
    workers = [DummyWorker(), DummyWorker()]
    threads = [DummyThread(), DummyThread()]
    # Simulate WorkerManager's internal registry
    wm = WorkerManager(logger=None)
    wm._worker_threads = list(zip(workers, threads))
    wm.shutdown_workers()
    for w in workers:
        assert w.stopped or w.canceled
    for t in threads:
        assert t.quit_called
        assert t.wait_called
    # Registry should be cleared
    assert not wm._worker_threads
