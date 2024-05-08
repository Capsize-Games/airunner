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
        self.publisher_signals = [
            SignalCode.LLM_LOAD_SIGNAL
        ]

    def handle_publish_message(self, data: object):
        print("PUBLISH MESSAGE", data)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()

        if loop.is_running():
            loop.create_task(self.publish_message({
                "action": SignalCode.LLM_LOAD_SIGNAL.value,
                "data": data
            }))
        else:
            asyncio.run(self.publish_message({
                "action": SignalCode.LLM_LOAD_SIGNAL.value,
                "data": data
            }))


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
        if code in self.publisher_signals:
            self.mediator.register(code, self.handle_publish_message)
        else:
            self.mediator.register(code, slot_function)
