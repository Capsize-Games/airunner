from typing import Callable

from datasynth.messager.publisher import PublisherMixin

from airunner.enums import SignalCode
from airunner.signal_mediator import SignalMediator
import asyncio


class MediatorMixin(PublisherMixin):
    """
    Use with any class that needs to emit and receive signals.
    Initialize with a SignalMediator instance.
    """
    def __init__(self):
        PublisherMixin.__init__(self, subject="llm_action_queue")
        self.threads = []
        self.workers = []
        self.mediator = SignalMediator()
        self.publisher_signals = []

    def emit_signal(
        self,
        code: SignalCode,
        data: object = None
    ):
        self.mediator.emit_signal(code, data)

    def register(
        self,
        code: SignalCode,
        slot_function: Callable
    ):
        """
        Accessor method for SignalMediator. register method.
        :param code:
        :param slot_function:
        :return:
        """
        self.mediator.register(code, slot_function)
