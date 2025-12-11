import traceback
from typing import Dict, Optional, Callable as CallableType
import inspect
from typing import Callable
from PySide6.QtCore import QObject, Signal as BaseSignal, Slot
from airunner.enums import SignalCode
import weakref
import threading
import queue
from airunner.utils.application.get_logger import get_logger

logger = get_logger(__name__)


class SingletonMeta(type):
    """
    Metaclass used to create a Singleton instance of a class.
    """

    _instances: Dict = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class _SignalEmitter(QObject):
    """
    Helper QObject to provide a per-instance signal for Signal.
    """

    signal = BaseSignal(dict)


class Signal(QObject):
    """
    Represents a signal that can be emitted and received.
    """

    def __init__(self, callback: Callable):
        super().__init__()
        # Store a weak reference to the callback to avoid keeping alive
        # QObject instances and to prevent invoking callbacks on destroyed
        # objects which can lead to segmentation faults.
        self._emitter = _SignalEmitter()
        self._emitter.signal.connect(self.on_signal_received)

        # Determine if the callback is a bound method
        if inspect.ismethod(callback):
            # If the bound method's instance is a QObject, keep a QPointer to
            # the underlying C++ object so we can detect when it has been
            # deleted at the C level (which would cause a segfault if we
            # attempted to call it). Also keep a WeakMethod to the Python
            # callable so we don't keep the instance alive.
            self._orig_func = callback.__func__
            self._orig_self = callback.__self__
            # If the bound instance is a QObject, connect to its destroyed
            # signal so we can detect C++-level deletion and avoid calling
            # into a deleted object (which may segfault).
            try:
                if isinstance(self._orig_self, QObject):
                    self._dead = False
                    try:
                        # destroyed passes the QObject as an argument; accept it
                        self._orig_self.destroyed.connect(
                            lambda obj=None: setattr(self, "_dead", True)
                        )
                    except Exception:
                        # If connecting fails, fall back to not having a dead flag
                        self._dead = False
                else:
                    self._dead = False
            except Exception:
                self._dead = False

            # WeakMethod will return None when the Python wrapper goes away
            self._callback_ref = weakref.WeakMethod(callback)
        else:
            # Regular function
            try:
                self._callback_ref = weakref.ref(callback)
            except TypeError:
                # Fallback: store strong ref if not weakrefable
                self._callback_ref = lambda: callback
            self._orig_func = callback
            self._orig_self = None

        try:
            # Try to inspect call signature; default to 1 param on failure
            resolved = None
            try:
                resolved = self._callback_ref()
            except Exception:
                resolved = None
            cb_for_sig = resolved if resolved is not None else callback
            self.param_count = len(inspect.signature(cb_for_sig).parameters)
        except (ValueError, TypeError, RecursionError):
            self.param_count = 1

    @Slot(object)
    def on_signal_received(self, data: Dict):
        logger.debug(f"Signal.on_signal_received CALLED")
        try:
            # Resolve the weak reference to get the live callable
            # If this Signal is tied to a QObject, ensure the underlying C++
            # object is still valid before resolving the weak method. If the
            # QPointer is null, the C++ object was deleted and calling into
            # Python wrappers can result in a segfault.
            # If we've been notified that the QObject has been destroyed,
            # skip calling the callback.
            if getattr(self, "_dead", False):
                logger.debug(f"Object is dead, skipping")
                return
            cb = None
            try:
                cb = self._callback_ref()
            except Exception as e2:
                logger.debug(f"Exception resolving callback: {e2}")
                cb = None

            if cb is None:
                # The Python callable has been garbage collected; skip
                logger.debug(f"Callback is None (garbage collected?)")
                return

            logger.debug(
                f"About to call callback: {cb} with param_count={self.param_count}"
            )
            if self.param_count == 0:
                cb()
            else:
                cb(data)
            logger.debug(f"allback completed")
        except Exception as e:
            # Print full traceback and context to aid debugging of signal handlers
            # Use a guarded traceback print: some traceback/inspect utilities
            # (e.g., inspect.getsource, linecache) can themselves trigger
            # RecursionError in complex C-extensions or patched importers.
            # We attempt the full traceback first, but fall back to a minimal
            # safe print if anything goes wrong while formatting the traceback.
            try:
                logger.error(
                    f"Error in signal callback: {e} (type: {type(e)})"
                )
                try:
                    print("data", data)
                except Exception:
                    print("data: <unprintable>")
                try:
                    # Avoid accessing potentially expensive attributes; use repr
                    cb = None
                    try:
                        cb = (
                            self._callback_ref()
                            if hasattr(self, "_callback_ref")
                            else None
                        )
                    except Exception:
                        cb = None
                    print("callback:", repr(cb))
                except Exception:
                    logger.error("callback: <unprintable>")
                # This can still raise (e.g., inspect.getsource), so guard it
                try:
                    traceback.print_exc()
                except RecursionError:
                    # Fallback: simple stack summary using traceback.format_exc may also fail,
                    # so provide a minimal representation of the exception.
                    logger.warning(
                        "Traceback unavailable due to recursion; exception repr below:"
                    )
                    try:
                        print(repr(e))
                    except Exception:
                        logger.error("<unrepresentable exception>")
            except RecursionError:
                # If even importing or using traceback triggers recursion, print minimal info
                try:
                    logger.debug(
                        "Error in signal callback (RecursionError during traceback formatting)"
                    )
                    try:
                        print("data", data)
                    except Exception:
                        logger.error("data: <unprintable>")
                    try:
                        cb = None
                        try:
                            cb = (
                                self._callback_ref()
                                if hasattr(self, "_callback_ref")
                                else None
                            )
                        except Exception:
                            cb = None
                        print("callback:", repr(cb))
                    except Exception:
                        print("callback: <unprintable>")
                except Exception:
                    # Last resort: suppress to avoid crashing the signal loop
                    pass

    # Add a property for backward compatibility
    @property
    def signal(self):
        return self._emitter.signal

    def matches(self, slot_function: Callable) -> bool:
        """
        Return True if the stored callback matches the provided slot_function.
        Used by SignalMediator.unregister to find the correct Signal wrapper.
        """
        if slot_function is None:
            return False
        if inspect.ismethod(slot_function):
            return (
                getattr(slot_function, "__func__", None) == self._orig_func
                and getattr(slot_function, "__self__", None) == self._orig_self
            )
        else:
            return slot_function == self._orig_func


class SignalMediator(metaclass=SingletonMeta):
    """
    Responsible for mediating signals between classes.

    Supports request-response correlation for HTTP API requests:
    - Tracks pending requests by request_id
    - Routes responses back to request callbacks
    - Supports both signal-based and callback-based patterns
    """

    def __init__(self, backend: Optional[object] = None):
        """
        Initialize the SignalMediator with an optional backend.
        :param backend: Custom backend for signal handling (e.g., RabbitMQ).
        """
        self.backend = backend
        self.signals = {} if backend is None else None

        # Request-response correlation support
        self._pending_requests: Dict[str, queue.Queue] = {}
        self._request_lock = threading.Lock()
        self._request_callbacks: Dict[str, CallableType] = {}

    def register(self, code: SignalCode, slot_function: Callable):
        """
        Register a signal to be received by a function.
        """
        if self.backend:
            # Delegate registration to the custom backend
            self.backend.register(code, slot_function)
        else:
            # Default PySide6-based implementation
            if code not in self.signals:
                self.signals[code] = []
            logger.info(
                f"SignalMediator: Registering {code} -> {slot_function.__name__ if hasattr(slot_function, '__name__') else slot_function}"
            )
            # Prevent duplicate registrations for the same callback
            for existing in list(self.signals[code]):
                try:
                    if existing.matches(slot_function):
                        logger.debug(
                            f"SignalMediator: Skipping duplicate registration for {code} -> {slot_function}"
                        )
                        return
                except Exception:
                    # If we cannot match, be conservative and continue
                    pass
            self.signals[code].append(Signal(callback=slot_function))

    def unregister(self, code: SignalCode, slot_function: Callable):
        """
        Unregister a previously registered slot function for a signal code.
        """
        if self.backend:
            # Delegate to backend if available
            try:
                self.backend.unregister(code, slot_function)
            except Exception:
                pass
            return

        if code not in self.signals:
            return
        # Remove signal wrappers that match the provided slot_function
        new_list = []
        for s in self.signals[code]:
            try:
                if s.matches(slot_function):
                    logger.info(
                        f"SignalMediator: Unregistering {code} -> {slot_function.__name__ if hasattr(slot_function, '__name__') else slot_function}"
                    )
                    # drop this signal wrapper
                    continue
            except Exception:
                # If something went wrong while matching, retain the signal
                pass
            new_list.append(s)
        self.signals[code] = new_list

    def emit_signal(self, code: SignalCode, data: Optional[Dict] = None):
        """
        Emit a signal to be received by a function.
        """
        data = {} if data is None else data

        # Check if this is a response to a pending request
        request_id = data.get("request_id")

        if request_id and request_id in self._pending_requests:
            # CRITICAL: Only route to callbacks if this is an actual RESPONSE
            # (has "response" key), not just the REQUEST signal echo.
            # Request signals have request_id but no response data.
            # Response signals have BOTH request_id and response data.
            is_response = "response" in data

            if is_response:
                # Route response to pending request queue
                with self._request_lock:
                    if request_id in self._pending_requests:
                        self._pending_requests[request_id].put(data)

                # Also call registered callback if exists
                with self._request_lock:
                    if request_id in self._request_callbacks:
                        try:
                            self._request_callbacks[request_id](data)
                        except Exception as e:
                            logger.error(
                                f"Error in request callback: {e}",
                                exc_info=True,
                            )
        elif "response" in data and not request_id:
            logger.warning(
                "SignalMediator.emit_signal received response without request_id; cannot route to pending request"
            )

        if self.backend:
            # Delegate emission to the custom backend
            self.backend.emit_signal(code, data)
        elif code in self.signals:
            for signal in self.signals[code]:
                try:
                    signal.signal.emit(data)
                except RuntimeError:
                    pass

    def register_pending_request(
        self, request_id: str, callback: Optional[CallableType] = None
    ):
        """Register a pending request for response correlation.

        Args:
            request_id: Unique identifier for the request
            callback: Optional callback to invoke when response arrives

        Returns:
            Queue that will receive responses for this request
        """
        with self._request_lock:
            response_queue = queue.Queue()
            self._pending_requests[request_id] = response_queue

            if callback:
                self._request_callbacks[request_id] = callback

            return response_queue

    def unregister_pending_request(self, request_id: str):
        """Unregister a pending request after completion or timeout.

        Args:
            request_id: Unique identifier for the request
        """
        with self._request_lock:
            self._pending_requests.pop(request_id, None)
            self._request_callbacks.pop(request_id, None)

    def wait_for_response(
        self, request_id: str, timeout: Optional[float] = None
    ) -> Optional[Dict]:
        """Wait for a response to a pending request.

        Args:
            request_id: Unique identifier for the request
            timeout: Optional timeout in seconds (None = block forever)

        Returns:
            Response data dict or None if timeout
        """
        with self._request_lock:
            response_queue = self._pending_requests.get(request_id)

        if not response_queue:
            return None

        try:
            return response_queue.get(timeout=timeout)
        except queue.Empty:
            return None
