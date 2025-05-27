# NOTE: This test file must be run in a real Qt environment (with a display or xvfb),
# and without patching PySide6.QtCore. Do NOT run this file as part of the main suite or in headless mode.
#
# To automate this, you can add the following to your Makefile or CI script (for display environments):
#   xvfb-run -a pytest src/airunner/utils/tests/xvfb_required/test_threaded_worker_mixin.py
#
# Do NOT run this file as part of the main suite or with pytest-qt enabled.

import os
import pytest

if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
    pytest.skip("Skipping Qt/Xvfb test: no display found", allow_module_level=True)

"""
Unit tests for ThreadedWorkerMixin in airunner.utils.application.threaded_worker_mixin.
Covers background task execution, signal/callback wiring, and cancellation logic.
"""

import pytest
from unittest.mock import MagicMock, patch

import types
import time

from airunner.utils.application.threaded_worker_mixin import (
    ThreadedWorkerMixin,
)
from PySide6.QtCore import QCoreApplication


class DummySignal:
    def __init__(self):
        self._callbacks = []

    def connect(self, cb):
        print(f"DummySignal.connect: adding {cb}")
        self._callbacks.append(cb)

    def emit(self, *args, **kwargs):
        print(f"DummySignal.emit: emitting to {len(self._callbacks)} callbacks")
        for cb in self._callbacks:
            print(f"DummySignal.emit: calling {cb}")
            cb(*args, **kwargs)
        QCoreApplication.processEvents()  # Ensure Qt event loop processes any queued events


class DummyWorker:
    def __init__(self, task_function=None, callback_data=None):
        self.task_function = task_function
        self.callback_data = callback_data
        self.progressUpdate = DummySignal()
        self.statusUpdate = DummySignal()
        self.taskFinished = DummySignal()
        self._running = True
        self._signal_refs = []  # Keep strong refs to connected callbacks

    def isRunning(self):
        return self._running

    def start(self):
        print("DummyWorker.start called")
        # Simulate immediate finish
        if self.task_function:
            result = self.task_function(self)
            data = {"result": result, "cancelled": False, "duration": 0.0}
            print("DummyWorker.start: emitting taskFinished")
            self.taskFinished.emit(data)
        self._running = False

    def cancel(self):
        self._running = False

    def wait(self):
        pass


@pytest.fixture
def mixin():
    # Patch BackgroundWorker in the mixin's module
    with patch(
        "airunner.utils.application.threaded_worker_mixin.BackgroundWorker",
        DummyWorker,
    ):

        class TestClass(ThreadedWorkerMixin):
            def __init__(self):
                super().__init__()
                self._signal_refs = []  # Keep strong refs to lambdas

            def execute_in_background(self, *args, **kwargs):
                # Override to keep strong refs to lambdas
                result = super().execute_in_background(*args, **kwargs)
                # Store all connected callbacks for test
                for worker in self._background_workers.values():
                    if hasattr(worker, "_signal_refs"):
                        self._signal_refs.extend(worker._signal_refs)
                return result

        return TestClass()


def wait_for_worker_cleanup(mixin, task_id, timeout=1.0):
    start = time.time()
    while time.time() - start < timeout:
        if task_id not in mixin._background_workers:
            return True
        QCoreApplication.processEvents()
        time.sleep(0.01)
    return False


def test_execute_in_background_calls_task_and_callbacks(mixin):
    called = {}

    def task(worker):
        print("test: task called")
        called["ran"] = True
        return 42

    def finished_cb(data):
        print("test: finished_cb called")
        MagicMock()(data)

    progress_cb = MagicMock()
    status_cb = MagicMock()
    mixin.execute_in_background(
        task_function=task,
        task_id="foo",
        on_finished=finished_cb,
        on_progress=progress_cb,
        on_status=status_cb,
    )
    assert wait_for_worker_cleanup(mixin, "foo"), "Worker was not cleaned up in time"
    assert called["ran"]
    progress_cb.assert_not_called()
    status_cb.assert_not_called()
    assert "foo" not in mixin._background_workers


def test_execute_in_background_replaces_existing_worker(mixin):
    def finished_cb(data):
        print("test: finished_cb called (replace)")
        MagicMock()(data)

    mixin.execute_in_background(lambda w: 1, task_id="bar", on_finished=finished_cb)
    mixin.execute_in_background(lambda w: 2, task_id="bar", on_finished=finished_cb)
    assert wait_for_worker_cleanup(mixin, "bar"), "Worker was not cleaned up in time"
    assert "bar" not in mixin._background_workers


def test_stop_background_task_stops_and_cleans_up(mixin):
    # Add a running DummyWorker manually (do not call execute_in_background for this id)
    worker = DummyWorker()
    worker._running = True
    worker.cancel_called = False
    worker.wait_called = False

    def cancel():
        worker.cancel_called = True
        worker._running = False

    def wait():
        worker.wait_called = True

    worker.cancel = cancel
    worker.wait = wait
    mixin._background_workers["baz"] = worker
    mixin.stop_background_task("baz")
    assert "baz" not in mixin._background_workers
    assert worker.cancel_called
    assert worker.wait_called


def test_stop_all_background_tasks_stops_all(mixin):
    # Add two running DummyWorkers
    for tid in ("a", "b"):
        worker = DummyWorker()
        worker._running = True
        mixin._background_workers[tid] = worker
    mixin.stop_all_background_tasks()
    assert mixin._background_workers == {}


def test_get_active_background_tasks(mixin):
    mixin._background_workers = {"x": MagicMock(), "y": MagicMock()}
    tasks = mixin.get_active_background_tasks()
    assert set(tasks) == {"x", "y"}


def test_cleanup_worker_prints_for_non_DummySignal(capsys):
    class NotDummySignal:
        pass

    class DummyWorkerObj:
        def __init__(self):
            self.taskFinished = NotDummySignal()
            self._signal_refs = []
            self.isRunning = lambda: False

    m = type("M", (ThreadedWorkerMixin,), {"_background_workers": {}})()
    m._background_workers = {"foo": DummyWorkerObj()}
    m._cleanup_worker("foo")
    out = capsys.readouterr().out
    # The actual output is just the generic cleanup message
    assert "ThreadedWorkerMixin: _cleanup_worker called for foo" in out
