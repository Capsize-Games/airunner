from typing import Any
import queue
from abc import abstractmethod, ABC, ABCMeta

from PySide6.QtCore import Signal, QThread, QObject

from airunner.enums import QueueType, SignalCode, WorkerState
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.settings import AIRUNNER_SLEEP_TIME_IN_MS
from airunner.gui.windows.main.settings_mixin import SettingsMixin

QObjectMeta = type(QObject)


class CombinedMeta(QObjectMeta, ABCMeta):
    pass


class Worker(
    MediatorMixin, SettingsMixin, QObject, ABC, metaclass=CombinedMeta
):
    queue_type = QueueType.GET_NEXT_ITEM
    finished = Signal()
    prefix = "Worker"

    def __init__(self, sleep_time_in_ms: int = AIRUNNER_SLEEP_TIME_IN_MS):
        super().__init__()
        self._sleep_time_in_ms: int = sleep_time_in_ms
        self.state = WorkerState.HALTED
        self.running = False
        self.queue = queue.Queue()
        self.items = {}
        self.current_index = 0
        self.paused = False
        self.register(SignalCode.QUIT_APPLICATION, self.stop)

        # Remove thread creation and management from here
        # as it's handled by create_worker function

    @abstractmethod
    def handle_message(self, message: Any):
        raise NotImplementedError

    def start_worker_thread(self):
        """
        This method is kept for backward compatibility
        but actual thread management is handled by create_worker
        """
        pass

    def start(self):
        """Start the worker's processing loop"""
        self.run()

    def run(self):
        if self.queue_type is QueueType.NONE:
            return
        self.logger.debug("Starting worker")
        self.running = True
        while self.running:
            self.preprocess()
            self.run_thread()

    def run_thread(self):
        """
        For most workers you can override
        the handle_message method and leave this
        default run_thread implmentation in place.
        """
        try:
            msg = self.get_item_from_queue()
            if msg is not None:
                self.handle_message(msg)
        except queue.Empty:
            pass
        if self.paused:
            self.logger.debug("Paused")
            while self.paused:
                QThread.msleep(self._sleep_time_in_ms)
            self.logger.debug("Resumed")
        QThread.msleep(self._sleep_time_in_ms)

    def preprocess(self):
        pass

    def clear_queue(self):
        self.queue = queue.Queue()

    def get_item_from_queue(self):
        if self.queue_type == QueueType.GET_LAST_ITEM:
            msg = self.get_last_item()
        else:
            msg = self.get_next_item()
        return msg

    def get_last_item(self):
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

    def add_to_queue(self, message):
        if (
            type(message) is dict
            and "options" in message
            and message["options"]["empty_queue"]
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
