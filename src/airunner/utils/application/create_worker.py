from PySide6.QtCore import QThread


WORKERS = []
THREADS = []


def create_worker(worker_class_, **kwargs):
    # Patch for test isolation: if AIRUNNER_TEST_MODE is set, do not start real threads
    worker = worker_class_(**kwargs)
    # get existing QApplication instance
    worker_thread = QThread()
    worker.moveToThread(worker_thread)
    worker.finished.connect(worker_thread.quit)

    # Change this connection to directly call the run method
    # instead of start, since start now just calls run
    worker_thread.started.connect(worker.run)

    worker_thread.start()
    WORKERS.append(worker)
    THREADS.append(worker_thread)
    return worker
