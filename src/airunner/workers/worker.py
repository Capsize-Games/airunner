import queue

from PyQt6.QtCore import pyqtSignal, pyqtSlot, QThread, QSettings, QObject

from airunner.aihandler.logger import Logger
from airunner.mediator_mixin import MediatorMixin


class Worker(QObject, MediatorMixin):
    queue_type = "get_next_item"
    finished = pyqtSignal()

    @property
    def settings(self):
        return self.application_settings.value("settings")
    
    def __init__(self, prefix="Worker"):
        self.prefix = prefix
        super().__init__()
        MediatorMixin.__init__(self)
        self.logger = Logger(prefix=prefix)
        self.running = False
        self.queue = queue.Queue()
        self.items = {}
        self.current_index = 0
        self.paused = False
        self.application_settings = QSettings("Capsize Games", "AI Runner")
        self.register("application_settings_changed_signal", self)
        self.update_properties()
    
    @pyqtSlot()
    def on_application_settings_changed_signal(self):
        self.update_properties()
    
    def update_properties(self):
        pass

    pyqtSlot()
    def start(self):
        self.logger.info("Starting")
        self.running = True
        while self.running:
            try:
                # if self.queue has more than one item, scrap everything other than the last item that
                # was added to the queue
                msg = self.get_item_from_queue()
                if msg is not None:
                    self.handle_message(msg)
                else:
                    self.logger.warning("No message")
            except queue.Empty:
                msg = None
            if self.paused:
                self.logger.info("Paused")
                while self.paused:
                    QThread.msleep(100)
                self.logger.info("Resumed")
            QThread.msleep(1)
    
    def get_item_from_queue(self):
        if self.queue_type == "get_last_item":
            msg = self.get_last_item()
        else:
            msg = self.get_next_item()
        return msg
    
    def get_last_item(self):
        msg = None
        index = self.queue.get()
        msg = self.items.pop(index, None)
        self.items = {}
        self.queue.empty()
        return msg

    def get_next_item(self):
        index = self.queue.get()
        msg = self.items.pop(index, None)
        return msg

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def handle_message(self, message):
        self.emit(self.prefix + "_response_signal", message)

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