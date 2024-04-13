from PySide6.QtCore import QThread

WORKERS = []
THREADS = []


def create_worker(worker_class_):
    prefix = worker_class_.__name__
    worker = worker_class_(prefix=prefix)
    worker_thread = QThread()
    worker.moveToThread(worker_thread)
    worker.finished.connect(worker_thread.quit)
    worker_thread.started.connect(worker.start)
    worker_thread.start()
    WORKERS.append(worker)
    THREADS.append(worker_thread)
    return worker
