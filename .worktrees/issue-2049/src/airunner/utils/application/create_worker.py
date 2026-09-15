from PySide6.QtCore import QThread


WORKERS = []
THREADS = []


def create_worker(worker_class_, **kwargs):
    # Patch for test isolation: if AIRUNNER_TEST_MODE is set, do not start real threads
    worker = worker_class_(**kwargs)
    worker_name = getattr(worker_class_, "__name__", worker.__class__.__name__)
    try:
        worker.setObjectName(worker_name)
    except Exception:
        pass

    # get existing QApplication instance
    worker_thread = QThread()
    worker_thread.setObjectName(worker_name)
    worker.moveToThread(worker_thread)
    worker.finished.connect(worker_thread.quit)
    worker_thread.finished.connect(worker.deleteLater)
    worker_thread.finished.connect(worker_thread.deleteLater)

    # Change this connection to directly call the run method
    # instead of start, since start now just calls run
    worker_thread.started.connect(worker.run)

    worker_thread.start()
    WORKERS.append(worker)
    THREADS.append(worker_thread)
    return worker
