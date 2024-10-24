import inspect
import queue
import threading

from PySide6.QtCore import Signal, QThread, QObject

from airunner.enums import QueueType, SignalCode, WorkerState
from airunner.mediator_mixin import MediatorMixin
from airunner.settings import SLEEP_TIME_IN_MS
from airunner.windows.main.settings_mixin import SettingsMixin


class Worker(QObject, MediatorMixin, SettingsMixin):
    queue_type = QueueType.GET_NEXT_ITEM
    finished = Signal()
    prefix = "Worker"

    def __init__(self, signals=None):
        self.signals = signals or []
        MediatorMixin.__init__(self)
        
        super().__init__()
        self.state = WorkerState.HALTED
        self.running = False
        self.queue = queue.Queue()
        self.items = {}
        self.current_index = 0
        self.paused = False
        self.register(SignalCode.QUIT_APPLICATION, self.stop)
        self.register_signals()

        threading.Thread(target=self.start_worker_thread).start()

    def start_worker_thread(self):
        pass

    def register_signals(self):
        for signal in self.signals:
            self.register(signal[0], signal[1])

    def start(self):
        import traceback
        traceback.format_exc()
        self.run()

    def run(self):
        if self.queue_type == QueueType.NONE:
            return
        self.logger.debug("Starting worker")
        self.running = True
        while self.running:
            self.preprocess()
            try:
                msg = self.get_item_from_queue()
                if msg is not None:
                    if len(inspect.signature(self.handle_message).parameters) == 0:
                        self.handle_message()
                    else:
                        self.handle_message(msg)
            except queue.Empty:
                msg = None
            if self.paused:
                self.logger.debug("Paused")
                while self.paused:
                    QThread.msleep(SLEEP_TIME_IN_MS)
                self.logger.debug("Resumed")
            QThread.msleep(SLEEP_TIME_IN_MS)

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
            try:
                index = self.queue.get_nowait()
                if index in self.items:
                    break
            except queue.Empty:
                pass
        if index in self.items:
            msg = self.items.pop(index)
            self.items = {}
            self.queue.empty()
            return msg
        else:
            return None

    def get_next_item(self):
        try:
            index = self.queue.get_nowait()
            msg = self.items.pop(index, None)
            return msg
        except queue.Empty:
            return None

    def pause(self):
        self.state = WorkerState.PAUSED

    def unpause(self):
        if self.state == WorkerState.PAUSED:
            self.state = WorkerState.RUNNING

    def resume(self):
        self.paused = False

    def handle_message(self, message):
        raise NotImplementedError

    def add_to_queue(self, message):
        if (
            type(message) is dict and
            "options" in message and
            message["options"]["empty_queue"]
        ):
            self.empty_queue()

        if self.queue_type == QueueType.GET_LAST_ITEM:
            self.items = {}
            self.queue.empty()
            self.current_index = 0

        self.items[self.current_index] = message
        self.queue.put(self.current_index)
        self.current_index += 1

    def empty_queue(self):
        self.queue = queue.Queue()
        self.items = {}
        self.current_index = 0

    def stop(self):
        self.logger.debug("Stopping")
        self.running = False
        self.finished.emit()

    def cancel(self):
        self.logger.debug("Canceling")
        while not self.queue.empty():
            self.queue.get()
