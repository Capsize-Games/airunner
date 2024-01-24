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

    def register(self, signal_name, slot_parent, slot_function=None):
        """
        Register a signal to be received by a class.

        :param signal_name: The name of the signal to register
        :param slot_parent: The class that will receive the signal, and must have an on_{signal_name} method.
        :param slot_function: The optional function to call when the signal is received. If not provided, the
        slot_parent's on_{signal_name} method will be called.
        """
        if signal_name not in self.signals:
            # Create a new Signal instance for this signal name
            self.signals[signal_name] = Signal()
        # Connect the Signal's pyqtSignal to receive the method of the slot parent
        try:
            if slot_function:
                # If a slot function is provided, connect the Signal's pyqtSignal to that function
                self.signals[signal_name].signal.connect(slot_function)
            else:
                # If a slot function is not provided, connect the Signal's pyqtSignal to the slot parent's
                self.signals[signal_name].signal.connect(getattr(slot_parent, f"on_{signal_name}"))
        except Exception as e:
            print(f"Error connecting signal {signal_name}", e)

    def emit(self, signal_name, data=None):
        """
        Emit a signal.
        :param signal_name:
        :param data:
        :return:
        """
        if signal_name in self.signals:
            self.signals[signal_name].signal.emit(data)
