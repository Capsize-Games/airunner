"""Worker-thread helpers shared by service and GUI compatibility imports."""

from __future__ import annotations

from airunner_services.utils.application.runtime_primitives import QThread


WORKERS = []
THREADS = []


def create_worker(worker_class_: type, **kwargs: object) -> object:
    """Create one worker object on its own Qt thread."""
    worker = worker_class_(**kwargs)
    worker_name = getattr(worker_class_, "__name__", worker.__class__.__name__)
    try:
        worker.setObjectName(worker_name)
    except Exception:
        pass

    worker_thread = QThread()
    worker_thread.setObjectName(worker_name)
    worker.moveToThread(worker_thread)
    worker.finished.connect(worker_thread.quit)
    worker_thread.finished.connect(worker.deleteLater)
    worker_thread.finished.connect(worker_thread.deleteLater)
    worker_thread.started.connect(worker.run)

    worker_thread.start()
    WORKERS.append(worker)
    THREADS.append(worker_thread)
    return worker


__all__ = ["THREADS", "WORKERS", "create_worker"]
