"""Service-owned runtime primitives that avoid direct Qt dependencies."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any, Optional


class _BoundSignal:
    """Store callbacks for one signal bound to one object instance."""

    def __init__(self) -> None:
        self._callbacks: list[Callable[..., Any]] = []
        self._lock = threading.Lock()

    def connect(self, callback: Callable[..., Any]) -> None:
        """Register one callback when it is not already connected."""
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def disconnect(self, callback: Callable[..., Any]) -> None:
        """Remove one callback when it is present."""
        with self._lock:
            self._callbacks = [
                existing
                for existing in self._callbacks
                if existing != callback
            ]

    def emit(self, *args: Any, **kwargs: Any) -> None:
        """Invoke each connected callback with the provided payload."""
        with self._lock:
            callbacks = list(self._callbacks)
        for callback in callbacks:
            callback(*args, **kwargs)


class Signal:
    """Descriptor that exposes one bound signal per object instance."""

    def __init__(self, *_args: object) -> None:
        self._storage_name = ""

    def __set_name__(self, _owner: type, name: str) -> None:
        """Remember the instance attribute used for this bound signal."""
        self._storage_name = f"__service_signal_{name}"

    def __get__(self, instance: object, _owner: type | None = None) -> Any:
        """Return the descriptor on the class or one bound signal."""
        if instance is None:
            return self
        signal = getattr(instance, self._storage_name, None)
        if signal is None:
            signal = _BoundSignal()
            setattr(instance, self._storage_name, signal)
        return signal


class QObject:
    """Minimal object API used by service-owned runtime code."""

    destroyed = Signal()

    def __init__(self, *args: object, **kwargs: object) -> None:
        self._object_name = ""
        self._thread = None
        super().__init__(*args, **kwargs)

    def setObjectName(self, name: str) -> None:
        """Store one object name for diagnostics compatibility."""
        self._object_name = name

    def objectName(self) -> str:
        """Return the currently stored object name."""
        return self._object_name

    def moveToThread(self, thread: object) -> None:
        """Keep the legacy worker API surface without Qt affinity."""
        self._thread = thread

    def thread(self) -> object | None:
        """Return the thread reference last assigned to this object."""
        return self._thread

    def deleteLater(self) -> None:
        """Emit destruction callbacks immediately in service mode."""
        self.destroyed.emit()


class QThread(QObject):
    """Small thread wrapper compatible with the old Qt worker API."""

    started = Signal()
    finished = Signal()

    def __init__(self, *args: object, **kwargs: object) -> None:
        self._thread: Optional[threading.Thread] = None
        super().__init__(*args, **kwargs)

    def start(self) -> None:
        """Start one daemon thread unless it is already running."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        """Emit start and finish notifications around thread work."""
        try:
            self.started.emit()
        finally:
            self.finished.emit()

    def quit(self) -> None:
        """Keep the Qt-compatible API surface for worker shutdown."""

    @staticmethod
    def msleep(milliseconds: int) -> None:
        """Sleep for the requested number of milliseconds."""
        time.sleep(max(milliseconds, 0) / 1000)


class QCoreApplication(QObject):
    """Headless application singleton used by the service layer."""

    _instance: Optional["QCoreApplication"] = None

    def __init__(self, _args: Optional[list[object]] = None) -> None:
        del _args
        super().__init__()
        self._quit_requested = False
        self.__class__._instance = self

    @classmethod
    def instance(cls) -> Optional["QCoreApplication"]:
        """Return the currently active application instance."""
        return cls._instance

    def processEvents(self) -> None:
        """Keep the Qt-compatible event processing hook as a no-op."""

    def quit(self) -> None:
        """Record one quit request for compatibility with old code paths."""
        self._quit_requested = True


class QTimer(QObject):
    """Simple repeating timer used for service-side background polling."""

    timeout = Signal()

    def __init__(self, *args: object, **kwargs: object) -> None:
        self._interval_seconds = 0.0
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        super().__init__(*args, **kwargs)

    def start(self, milliseconds: int) -> None:
        """Start one repeating timer with the provided interval."""
        self.stop()
        self._interval_seconds = max(milliseconds, 0) / 1000
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        """Emit timeout callbacks until the timer is stopped."""
        while not self._stop_event.wait(self._interval_seconds):
            self.timeout.emit()

    def stop(self) -> None:
        """Stop the timer when it is active."""
        self._stop_event.set()

    def deleteLater(self) -> None:
        """Stop background timer work before dispatching destruction."""
        self.stop()
        super().deleteLater()


QApplication = QCoreApplication


def Slot(*_args: object, **_kwargs: object) -> Callable[[Callable], Callable]:
    """Return a no-op decorator compatible with Qt slot annotations."""

    def _decorator(function: Callable) -> Callable:
        return function

    return _decorator


__all__ = [
    "QApplication",
    "QCoreApplication",
    "QObject",
    "QThread",
    "QTimer",
    "Signal",
    "Slot",
]