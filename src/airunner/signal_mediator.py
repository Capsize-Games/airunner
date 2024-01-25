from PyQt6.QtCore import QObject, pyqtSignal

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
    signal = pyqtSignal(object)


class SignalMediator(metaclass=SingletonMeta):
    """
    This class is responsible for mediating signals between classes.
    """
    def __init__(self):
        self.signals = {}

    def register(
        self,
        code: SignalCode,
        slot_function: object
    ):
        """
        Register a signal to be received by a class.

        :param code: The SignalCode of the signal to register
        :param slot_function: The function to call when the signal is received.
        """
        if code not in self.signals:
            # Create a new Signal instance for this signal name
            self.signals[code] = Signal()
        # Connect the Signal's pyqtSignal to receive the method of the slot parent
        try:
            self.signals[code].signal.connect(slot_function)
        except Exception as e:
            print(f"Error connecting signal {code}", e)

    def emit(
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
        if code in self.signals:
            self.signals[code].signal.emit(data)
