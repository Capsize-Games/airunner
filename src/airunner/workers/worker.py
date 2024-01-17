import queue
from PyQt6 import QtCore

from airunner.aihandler.logger import Logger


class Worker(QtCore.QObject):
    response_signal = QtCore.pyqtSignal(dict)
    finished = QtCore.pyqtSignal()
    queue_type = "get_next_item"
    
    def __init__(self, prefix="Worker"):
        super().__init__()
        self.logger = Logger(prefix=prefix)
        self.running = False
        self.queue = queue.Queue()
        self.items = {}
        self.current_index = 0
        self.paused = False

    @QtCore.pyqtSlot()
    def start(self):
        self.logger.info("Starting")
        self.running = True
        while self.running:
            try:
                # if self.queue has more than one item, scrap everything other than the last item that
                # was added to the queue
                msg = self.get_item_from_queue()
                if msg:
                    self.handle_message(msg)
            except queue.Empty:
                msg = None
            if self.paused:
                self.logger.info("Paused")
                while self.paused:
                    QtCore.QThread.msleep(100)
                self.logger.info("Resumed")
            QtCore.QThread.msleep(100)
    
    def get_item_from_queue(self):
        if self.queue_type == "get_last_item":
            msg = self.get_last_item()
        else:
            msg = self.get_next_item()
        return msg
    
    def get_last_item(self):
        msg = None
        while not self.queue.empty():
            index = self.queue.get(timeout=0.1)
            if index is not None:
                msg = self.items.pop(index, None)
        return msg

    def get_next_item(self):
        index = self.queue.get(timeout=0.1)
        msg = self.items.pop(index, None)
        return msg

    
    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

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