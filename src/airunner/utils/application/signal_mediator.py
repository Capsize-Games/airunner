from typing import Dict, Optional
import inspect
from typing import Callable
from PySide6.QtCore import QObject, Signal as BaseSignal, Slot
from airunner.enums import SignalCode
import weakref


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
        try:
            # Resolve the weak reference to get the live callable
            # If this Signal is tied to a QObject, ensure the underlying C++
            # object is still valid before resolving the weak method. If the
            # QPointer is null, the C++ object was deleted and calling into
            # Python wrappers can result in a segfault.
            # If we've been notified that the QObject has been destroyed,
            # skip calling the callback.
            if getattr(self, "_dead", False):
                return
            cb = None
            try:
                cb = self._callback_ref()
            except Exception:
                cb = None

            if cb is None:
                # The Python callable has been garbage collected; skip
                return

            if self.param_count == 0:
                cb()
            else:
                cb(data)
        except Exception as e:
            # Print full traceback and context to aid debugging of signal handlers
            import traceback

            print(f"Error in signal callback: {e} (type: {type(e)})")
            try:
                print("data", data)
            except Exception:
                print("data: <unprintable>")
            try:
                print("callback", self.callback)
            except Exception:
                print("callback: <unprintable>")
            traceback.print_exc()

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
    """

    def __init__(self, backend: Optional[object] = None):
        """
        Initialize the SignalMediator with an optional backend.
        :param backend: Custom backend for signal handling (e.g., RabbitMQ).
        """
        self.backend = backend
        self.signals = {} if backend is None else None

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

            # Remove any Signal wrappers whose callback matches the given function
            remaining = []
            for s in self.signals.get(code, []):
                try:
                    if hasattr(s, "matches") and s.matches(slot_function):
                        # skip this one (i.e. remove)
                        continue
                except Exception:
                    pass
                remaining.append(s)

            if remaining:
                self.signals[code] = remaining
            else:
                # No remaining handlers for this code
                if code in self.signals:
                    del self.signals[code]

    def emit_signal(self, code: SignalCode, data: Optional[Dict] = None):
        """
        Emit a signal to be received by a function.
        """
        data = {} if data is None else data
        if self.backend:
            # Delegate emission to the custom backend
            self.backend.emit_signal(code, data)
        elif code in self.signals:
            for signal in self.signals[code]:
                try:
                    signal.signal.emit(data)
                except RuntimeError as e:
                    pass
