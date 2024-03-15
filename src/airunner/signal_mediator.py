from typing import Callable

from PySide6.QtCore import QObject, Signal as BaseSignal

from airunner.enums import SignalCode


class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class Signal(QObject):
    """
    This class represents a signal that can be emitted and received.
    """
    signal = BaseSignal(dict)

    def __init__(self, callback: Callable):
        super().__init__()
        self.callback = callback

        self.signal.connect(self.on_signal_received)

    def on_signal_received(self, data: dict):
        try:
            self.callback(data)
        except TypeError:
            self.callback()


SIGNALS = {}

class SignalMediator(metaclass=SingletonMeta):
    """
    This class is responsible for mediating signals between classes.
    """

    def register(
        self,
        code: SignalCode,
        slot_function: Callable
    ):
        """
        Register a signal to be received by a class.

        :param code: The SignalCode of the signal to register
        :param slot_function: The function to call when the signal is received.
        """
        if code not in SIGNALS:
            # Create a new Signal instance for this signal name
            SIGNALS[code] = Signal(callback=slot_function)
        # Connect the Signal's Signal to receive the method of the slot parent
        try:
            SIGNALS[code].signal.connect(slot_function)
        except Exception as e:
            print(f"Error connecting signal {code}", e)

    def emit_signal(
        self,
        code: SignalCode,
        data: object = None
    ):
        """
        Emit a signal.
        :param code:
        :param data:
        :return:
        """
        if code in SIGNALS:
            SIGNALS[code].signal.emit(data)
