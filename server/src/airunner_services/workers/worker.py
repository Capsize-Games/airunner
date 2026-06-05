"""Service-owned worker base class."""

from __future__ import annotations

import queue
from abc import ABC
from abc import abstractmethod
from enum import Enum
from typing import Any

from airunner_services.contract_enums import SignalCode
from airunner_services.settings import AIRUNNER_SLEEP_TIME_IN_MS
from airunner_services.utils.application import get_logger
from airunner_services.utils.application import MediatorMixin
from airunner_services.utils.application.runtime_context_mixin import (
    RuntimeContextMixin,
)
from airunner_services.utils.application.runtime_primitives import QObject
from airunner_services.utils.application.runtime_primitives import QThread
from airunner_services.utils.application.runtime_primitives import Signal


class QueueType(Enum):
    """Fallback queue types for service-owned workers."""

    GET_LAST_ITEM = 100
    GET_NEXT_ITEM = 200
    NONE = 300


class WorkerState(Enum):
    """Fallback worker states for service-owned workers."""

    HALTED = "halted"
    PAUSED = "paused"
    RUNNING = "running"


class Worker(
    RuntimeContextMixin,
    MediatorMixin,
    QObject,
    ABC,
):
    """Provide shared queue and signal behavior for service workers."""

    queue_type = QueueType.GET_NEXT_ITEM
    finished = Signal()
    prefix = "Worker"

    def __init__(
        self,
        sleep_time_in_ms: int = AIRUNNER_SLEEP_TIME_IN_MS,
        *args: object,
        **kwargs: object,
    ) -> None:
        self.logger = get_logger(self.__class__.__module__)
        super().__init__(*args, **kwargs)
        self._sleep_time_in_ms = sleep_time_in_ms
        self.state = WorkerState.HALTED
        self.running = False
        self.queue = queue.Queue()
        self.items: dict[int, Any] = {}
        self.current_index = 0
        self.paused = False
        self.register(SignalCode.QUIT_APPLICATION, self.stop)

    @abstractmethod
    def handle_message(self, message: Any) -> None:
        """Handle one queued worker payload."""

    def start_worker_thread(self) -> None:
        """Keep the legacy worker API shape for compatibility."""

    def start(self) -> None:
        """Start the worker processing loop."""
        self.run()

    def run(self) -> None:
        """Run the queue-processing loop until stopped."""
        if self._queue_type_matches("NONE"):
            return
        self.logger.debug("Starting worker")
        self.running = True
        while self.running:
            self.preprocess()
            self.run_thread()

    def run_thread(self) -> None:
        """Process one queued item when available."""
        try:
            message = self.get_item_from_queue()
            if message is not None:
                self.handle_message(message)
        except queue.Empty:
            pass
        except Exception:
            self.logger.exception(
                "Unhandled exception in %s.run_thread",
                self.__class__.__name__,
            )
        if self.paused:
            while self.paused:
                QThread.msleep(self._sleep_time_in_ms)
        QThread.msleep(self._sleep_time_in_ms)

    def preprocess(self) -> None:
        """Hook for work that should happen before queue processing."""

    def clear_queue(self) -> None:
        """Clear all queued items."""
        self.queue = queue.Queue()

    def get_item_from_queue(self) -> Any:
        """Return the next queued item according to queue policy."""
        if self._queue_type_matches("GET_LAST_ITEM"):
            return self.get_last_item()
        return self.get_next_item()

    def get_last_item(self) -> Any:
        """Return the newest queued item and drop older entries."""
        index = None
        while not self.queue.empty():
            try:
                index = self.queue.get_nowait()
                if index in self.items:
                    break
            except queue.Empty:
                pass
        if index in self.items:
            message = self.items.pop(index)
            self.items = {}
            self.queue.empty()
            return message
        return None

    def get_next_item(self) -> Any:
        """Return the next queued item in FIFO order."""
        try:
            index = self.queue.get_nowait()
        except queue.Empty:
            return None
        return self.items.pop(index, None)

    def pause(self) -> None:
        """Mark the worker paused."""
        self.state = WorkerState.PAUSED

    def unpause(self) -> None:
        """Mark the worker running after a pause request."""
        if self.state == WorkerState.PAUSED:
            self.state = WorkerState.RUNNING

    def resume(self) -> None:
        """Resume active processing after a hard pause."""
        self.paused = False

    def add_to_queue(self, message: Any) -> None:
        """Queue one message for worker processing."""
        if (
            isinstance(message, dict)
            and "options" in message
            and message["options"].get("empty_queue")
        ):
            self.empty_queue()
        if self._queue_type_matches("GET_LAST_ITEM"):
            self.items = {}
            self.queue.empty()
            self.current_index = 0
        self.items[self.current_index] = message
        self.queue.put(self.current_index)
        self.current_index += 1

    def empty_queue(self) -> None:
        """Reset worker queue state."""
        self.queue = queue.Queue()
        self.items = {}
        self.current_index = 0

    def stop(self) -> None:
        """Stop the worker loop and emit the finished signal."""
        self.logger.debug("Stopping")
        self.running = False
        self.finished.emit()

    def cancel(self) -> None:
        """Drop any queued work without stopping the worker loop."""
        self.logger.debug("Canceling")
        while not self.queue.empty():
            self.queue.get()

    def _queue_type_matches(self, expected_name: str) -> bool:
        """Return whether the active queue type matches one expected name."""
        queue_type = getattr(self, "queue_type", None)
        if getattr(queue_type, "name", None) == expected_name:
            return True
        expected = getattr(QueueType, expected_name)
        value = getattr(queue_type, "value", queue_type)
        return value == expected.value or queue_type == expected


__all__ = ["QueueType", "Worker", "WorkerState"]
