from PyQt6.QtCore import QThread
from PyQt6.QtCore import pyqtSlot

from airunner.enums import SignalCode
from airunner.signal_mediator import SignalMediator


class MediatorMixin:
    """
    Use with any class that needs to emit and receive signals.
    Initialize with a SignalMediator instance.
    """
    def __init__(self):
        self.mediator = SignalMediator()
        self.threads = []
        
    def emit(
        self,
        code: SignalCode,
        data: object = None
    ):
        # Pass None as the second argument if no additional arguments are provided
        self.mediator.emit(code, data)

    pyqtSlot(object, object)
    def receive(self, signal_name, *args, **kwargs):
        method_name = f"on_{signal_name}"
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            method(*args, **kwargs)

    def register(
        self,
        code: SignalCode,
        slot_function: object
    ):
        """
        Accessor method for SignalMediator.register method.
        :param code:
        :param slot_function:
        :return:
        """
        self.mediator.register(code, slot_function)

    def create_worker(self, worker_class_):
        prefix = worker_class_.__name__
        worker = worker_class_(prefix=prefix)
        worker_thread = QThread()
        worker.moveToThread(worker_thread)
        worker.finished.connect(worker_thread.quit)
        worker_thread.started.connect(worker.start)
        worker_thread.start()
        self.threads.append(worker_thread)
        return worker
