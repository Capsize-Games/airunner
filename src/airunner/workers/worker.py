import queue

from PyQt6.QtCore import pyqtSignal, pyqtSlot, QThread, QSettings, QObject

from airunner.enums import QueueType, SignalCode
from airunner.aihandler.logger import Logger
from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin


class Worker(QObject, MediatorMixin, SettingsMixin):
    queue_type = QueueType.GET_NEXT_ITEM
    finished = pyqtSignal()
    prefix = "Worker"

    def __init__(self, prefix=None):
        self.prefix = prefix or self.__class__.__name__
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super().__init__()
        self.logger = Logger(prefix=prefix)
        self.running = False
        self.queue = queue.Queue()
        self.items = {}
        self.current_index = 0
        self.paused = False
        self.application_settings = QSettings("Capsize Games", "AI Runner")
        self.register(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.on_application_settings_changed_signal)
        self.update_properties()
    
    def on_application_settings_changed_signal(self, _ignore):
        self.update_properties()
    
    def update_properties(self):
        pass

    pyqtSlot()
    def start(self):
        if self.queue_type == QueueType.NONE:
            return
        self.logger.info("Starting")
        self.running = True
        while self.running:
            self.preprocess()
            try:
                # if self.queue has more than one item, scrap everything other than the last item that
                # was added to the queue
                msg = self.get_item_from_queue()
                self.handle_message(msg)
            except queue.Empty:
                msg = None
            if self.paused:
                self.logger.info("Paused")
                while self.paused:
                    QThread.msleep(100)
                self.logger.info("Resumed")
            QThread.msleep(1)
    
    def preprocess(self):
        pass
    
    def get_item_from_queue(self):
        if self.queue_type == QueueType.GET_LAST_ITEM:
            msg = self.get_last_item()
        else:
            msg = self.get_next_item()
        return msg
    
    def get_last_item(self):
        msg = None
        index = None
        while not self.queue.empty():
            index = self.queue.get()
            if index in self.items:
                break
        if index in self.items:
            msg = self.items.pop(index)
            self.items = {}
            self.queue.empty()
            return msg
        else:
            return None

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