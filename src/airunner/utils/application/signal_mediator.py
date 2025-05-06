from typing import Dict, Optional
import inspect
from typing import Callable
from PySide6.QtCore import QObject, Signal as BaseSignal, Slot
from airunner.enums import SignalCode


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


class Signal(QObject):
    """
    Represents a signal that can be emitted and received.
    """

    signal: BaseSignal = BaseSignal(dict)

    def __init__(self, callback: Callable):
        super().__init__()
        self.callback = callback

        try:
            self.param_count = len(inspect.signature(self.callback).parameters)
        except (ValueError, TypeError, RecursionError):
            self.param_count = 1

        self.signal.connect(self.on_signal_received)

    @Slot(object)
    def on_signal_received(self, data: Dict):
        try:
            if self.param_count == 0:
                self.callback()
            else:
                self.callback(data)
        except Exception as e:
            self.logger.error(f"Error in signal callback: {e}")


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
                signal.signal.emit(data)
