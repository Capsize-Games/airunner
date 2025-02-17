from typing import Callable
from airunner.enums import SignalCode
from airunner.signal_mediator import SignalMediator

class MediatorMixin:
    """
    Use with any class that needs to emit and receive signals.
    Initialize with a SignalMediator instance.
    """
    def __init__(self, *args, **kwargs):
        self.mediator = SignalMediator()

    def emit_signal(self, code: SignalCode, data: object = None):
        self.mediator.emit_signal(code, data)

    def register(self, code: SignalCode, slot_function: Callable):
        """
        Accessor method for SignalMediator.register method.
        :param code:
        :param slot_function:
        :return:
        """
        self.mediator.register(code, slot_function)
