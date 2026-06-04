"""Signal mediator shared by the service runtime and GUI wrappers."""

from __future__ import annotations

import inspect
import logging
import os
import queue
import threading
import weakref
from collections.abc import Callable
from typing import Dict, Optional
from typing import Callable as CallableType

from airunner_services.utils.application.get_logger import get_logger


logger = get_logger(__name__)


def _trace_signal_registrations() -> bool:
    """Return whether verbose signal registration tracing is enabled."""
    return os.environ.get(
        "AIRUNNER_TRACE_SIGNAL_REGISTRATION",
        "0",
    ) == "1"


class SingletonMeta(type):
    """Metaclass used to create one Singleton instance per class."""

    _instances: Dict = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class Signal:
    """Represents one signal that can be emitted and received."""

    def __init__(self, callback: Callable):
        if inspect.ismethod(callback):
            self._orig_func = callback.__func__
            self._orig_self = callback.__self__
            self._callback_ref = weakref.WeakMethod(callback)
        else:
            try:
                self._callback_ref = weakref.ref(callback)
            except TypeError:
                self._callback_ref = lambda: callback
            self._orig_func = callback
            self._orig_self = None

        try:
            resolved = None
            try:
                resolved = self._callback_ref()
            except Exception:
                resolved = None
            cb_for_sig = resolved if resolved is not None else callback
            self.param_count = len(inspect.signature(cb_for_sig).parameters)
        except (ValueError, TypeError, RecursionError):
            self.param_count = 1

    def on_signal_received(self, data: Dict):
        """Resolve the callback and deliver one signal payload."""
        try:
            cb = None
            try:
                cb = self._callback_ref()
            except Exception:
                cb = None

            if cb is None:
                return

            if self.param_count == 0:
                cb()
            else:
                cb(data)
        except Exception as exc:
            logger.error(
                "Error in signal callback: %s (type: %s)",
                exc,
                type(exc),
            )
            if not logger.isEnabledFor(logging.DEBUG):
                return
            try:
                logger.exception("Signal callback traceback")
            except RecursionError:
                try:
                    logger.debug("Signal callback traceback unavailable")
                except Exception:
                    pass

    @property
    def signal(self):
        """Return one compatibility object that still exposes emit()."""
        return self

    def emit(self, data: Dict) -> None:
        """Deliver one signal payload through the stored callback."""
        self.on_signal_received(data)

    def matches(self, slot_function: Callable) -> bool:
        """Return whether the stored callback matches one slot function."""
        if slot_function is None:
            return False
        if inspect.ismethod(slot_function):
            return (
                getattr(slot_function, "__func__", None) == self._orig_func
                and getattr(slot_function, "__self__", None)
                == self._orig_self
            )
        return slot_function == self._orig_func


class SignalMediator(metaclass=SingletonMeta):
    """Coordinate signal registration, dispatch, and request correlation."""

    def __init__(self, backend: Optional[object] = None):
        self.backend = backend
        self.signals = {} if backend is None else None
        self._pending_requests: Dict[str, queue.Queue] = {}
        self._request_lock = threading.Lock()
        self._request_callbacks: Dict[str, CallableType] = {}

    @staticmethod
    def _normalize_code(code: object) -> object:
        """Return one comparable key for enum and non-enum signal codes."""
        return getattr(code, "value", code)

    def _find_signal_key(self, code: object) -> Optional[object]:
        """Return the stored signal key that matches one incoming code."""
        if code in self.signals:
            return code

        normalized = self._normalize_code(code)
        for existing_code in self.signals:
            if self._normalize_code(existing_code) == normalized:
                return existing_code
        return None

    def register(self, code: object, slot_function: Callable) -> None:
        """Register one callback for one signal key."""
        if self.backend:
            self.backend.register(code, slot_function)
            return

        signal_key = self._find_signal_key(code)
        if signal_key is None:
            signal_key = code
            self.signals[signal_key] = []
        if _trace_signal_registrations():
            logger.debug(
                "SignalMediator: Registering %s -> %s",
                code,
                (
                    slot_function.__name__
                    if hasattr(slot_function, "__name__")
                    else slot_function
                ),
            )
        for existing in list(self.signals[signal_key]):
            try:
                if existing.matches(slot_function):
                    if _trace_signal_registrations():
                        logger.debug(
                            "SignalMediator: Skipping duplicate "
                            "registration for %s -> %s",
                            code,
                            slot_function,
                        )
                    return
            except Exception:
                pass
        self.signals[signal_key].append(Signal(callback=slot_function))

    def unregister(self, code: object, slot_function: Callable) -> None:
        """Unregister one callback for one signal key."""
        if self.backend:
            try:
                self.backend.unregister(code, slot_function)
            except Exception:
                pass
            return

        signal_key = self._find_signal_key(code)
        if signal_key is None:
            return
        new_list = []
        for signal in self.signals[signal_key]:
            try:
                if signal.matches(slot_function):
                    if _trace_signal_registrations():
                        logger.debug(
                            "SignalMediator: Unregistering %s -> %s",
                            code,
                            (
                                slot_function.__name__
                                if hasattr(slot_function, "__name__")
                                else slot_function
                            ),
                        )
                    continue
            except Exception:
                pass
            new_list.append(signal)
        self.signals[signal_key] = new_list

    def emit(self, code: object, data: Optional[Dict] = None) -> None:
        """Backward-compatible alias for emit_signal."""
        self.emit_signal(code, data)

    def emit_signal(self, code: object, data: Optional[Dict] = None) -> None:
        """Emit one signal payload to all registered listeners."""
        data = {} if data is None else data
        request_id = data.get("request_id")

        if request_id and request_id in self._pending_requests:
            callback: Optional[CallableType] = None
            response_queue: Optional[queue.Queue] = None
            with self._request_lock:
                response_queue = self._pending_requests.get(request_id)
                callback = self._request_callbacks.get(request_id)
                if response_queue is not None:
                    response_queue.put(data)

            if callback is not None:
                try:
                    callback(data)
                except Exception as exc:
                    logger.error(
                        "Error in request callback: %s",
                        exc,
                        exc_info=True,
                    )

        if self.backend:
            self.backend.emit_signal(code, data)
            return

        signal_key = self._find_signal_key(code)
        if signal_key is not None:
            for signal in self.signals[signal_key]:
                try:
                    self._deliver_signal(signal, data)
                except RuntimeError:
                    pass

    @staticmethod
    def _deliver_signal(signal: Signal, data: Dict) -> None:
        """Deliver one signal payload with headless-safe semantics."""
        signal.signal.emit(data)

    def register_pending_request(
        self,
        request_id: str,
        callback: Optional[CallableType] = None,
    ):
        """Register one pending request for response correlation."""
        with self._request_lock:
            response_queue = queue.Queue()
            self._pending_requests[request_id] = response_queue
            if callback:
                self._request_callbacks[request_id] = callback
            return response_queue

    def unregister_pending_request(self, request_id: str) -> None:
        """Remove one pending request after completion or timeout."""
        with self._request_lock:
            self._pending_requests.pop(request_id, None)
            self._request_callbacks.pop(request_id, None)

    def wait_for_response(
        self,
        request_id: str,
        timeout: Optional[float] = None,
    ) -> Optional[Dict]:
        """Wait for one correlated response or return None on timeout."""
        with self._request_lock:
            response_queue = self._pending_requests.get(request_id)

        if not response_queue:
            return None

        try:
            return response_queue.get(timeout=timeout)
        except queue.Empty:
            return None


__all__ = ["SignalMediator"]
