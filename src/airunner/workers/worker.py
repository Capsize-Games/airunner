import queue
from PyQt6 import QtCore

from airunner.aihandler.logger import Logger


class Worker(QtCore.QObject):
    response_signal = QtCore.pyqtSignal(dict)
    finished = QtCore.pyqtSignal()
    
    def __init__(self, prefix="Worker"):
        super().__init__()
        self.logger = Logger(prefix=prefix)
        self.running = False
        self.queue = queue.Queue()
        self.items = {}
        self.current_index = 0

    @QtCore.pyqtSlot()
    def start(self):
        self.logger.info("Starting")
        self.running = True
        while self.running:
            try:
                index = self.queue.get(timeout=0.1)
                msg = self.items.pop(index, None)
            except queue.Empty:
                msg = None
            if msg is not None:
                self.handle_message(msg)

    def handle_message(self, message):
        self.response_signal.emit(message)

    def add_to_queue(self, message):
        self.items[self.current_index] = message
        self.queue.put(self.current_index)
        self.current_index += 1
    
    def stop(self):
        self.logger.info("Stopping")
        self.running = False
        self.finished.emit()

    def cancel(self):
        self.logger.info("Canceling")
        while not self.queue.empty():
            self.queue.get()