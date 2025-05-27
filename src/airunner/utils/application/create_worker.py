from PySide6.QtCore import QThread


WORKERS = []
THREADS = []


def create_worker(worker_class_, *, registry=None, **kwargs):
    # Patch for test isolation: if AIRUNNER_TEST_MODE is set, do not start real threads
    import os

    if os.environ.get("AIRUNNER_TEST_MODE") == "1":
        from unittest.mock import MagicMock

        # Always return a tuple for test mode, matching production signature
        return MagicMock(), MagicMock()
    worker = worker_class_(**kwargs)
    # get existing QApplication instance
    worker_thread = QThread()
    worker.moveToThread(worker_thread)
    worker.finished.connect(worker_thread.quit)

    # Change this connection to directly call the run method
    # instead of start, since start now just calls run
    worker_thread.started.connect(worker.run)

    worker_thread.start()
    if registry is not None:
        registry.append((worker, worker_thread))
    return worker, worker_thread
