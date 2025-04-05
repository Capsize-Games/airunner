import json

from typing import Callable, Dict, Optional

from airunner.enums import SignalCode
from airunner.utils.application.signal_mediator import SignalMediator
from airunner.messaging.backends.rabbitmq_backend import RabbitMQBackend
from airunner.settings import AIRUNNER_MESSAGE_BACKEND


class MediatorMixin:
    """
    Use with any class that needs to emit and receive signals.
    Initialize with a SignalMediator instance.
    """

    _signal_handlers: Dict = {}

    def __init__(
        self,
        mediator: Optional[SignalMediator] = None,
        message_backend: Optional[Dict] = None,
        *args,
        **kwargs,
    ):
        """
        Initialize the mixin with an optional SignalMediator instance.
        :param mediator: Custom SignalMediator instance (e.g., with RabbitMQ backend).
        """
        if type(mediator) is not SignalMediator:
            mediator = None

        message_backend = message_backend or json.loads(
            AIRUNNER_MESSAGE_BACKEND or "{}"
        )

        if not mediator:
            backend = None
            if message_backend:
                backend_name = message_backend.pop("type", None)

                available_backends = {"rabbitmq": RabbitMQBackend}

                if backend_name in available_backends:
                    available_backends[backend_name](**message_backend)

            mediator = SignalMediator(backend=backend)

        self.mediator = mediator

        self.register_signals()
        super().__init__(*args, **kwargs)

    @property
    def signal_handlers(self) -> Dict:
        return self._signal_handlers

    @signal_handlers.setter
    def signal_handlers(self, value):
        self._signal_handlers = value

    def register_signals(self):
        """
        Set signal_handlers Dict in order to register signals.

        signal_handlers should be a dictionary of SignalCode enums and functions.
        Example:
        signal_handlers = {
            SignalCode.GET_SETTINGS: self.get_settings,
            SignalCode.SET_SETTINGS: self.set_settings
        }
        :return:
        """
        for signal, handler in self.signal_handlers.items():
            self.register(signal, handler)

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
