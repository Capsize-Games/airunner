from PyQt6.QtCore import QObject, pyqtSignal

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

    def register(self, signal_name, slot_parent):
        if signal_name not in self.signals:
            # Create a new Signal instance for this signal name
            self.signals[signal_name] = Signal()
        # Connect the Signal's pyqtSignal to the receive method of the slot parent
        try:
            self.signals[signal_name].signal.connect(getattr(slot_parent, f"on_{signal_name}"))
        except Exception as e:
            print(f"Error connecting signal {signal_name}", e)

    def emit(self, signal_name, data=None):
        if signal_name in self.signals:
            # Emit the Signal's pyqtSignal with two arguments
            self.signals[signal_name].signal.emit(data)