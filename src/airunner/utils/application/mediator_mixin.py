from typing import Callable, Dict, Optional

from airunner.enums import SignalCode
from airunner.utils.application.signal_mediator import SignalMediator


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
        :param mediator: Custom SignalMediator instance.
        """
        if type(mediator) is not SignalMediator:
            mediator = None

        if not mediator:
            mediator = SignalMediator()

        self.mediator = mediator

        # Ensure QObject initialization happens before we try to access signals
        super().__init__(*args, **kwargs)

        # Register signals for this instance
        self.register_signals()

        # Avoid Python callbacks during QObject destruction. PySide/Shiboken can
        # crash when worker-thread QObjects emit destroyed() while the wrapper is
        # being torn down. SignalMediator uses weak callback tracking instead.

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

    def unregister(self, code: SignalCode, slot_function: Callable):
        """Unregister one previously registered callback."""
        self.mediator.unregister(code, slot_function)

    def unregister_signals(self):
        """
        Unregister all signal handlers that were registered by this instance.
        """
        for code, handler in list(self.signal_handlers.items()):
            try:
                self.mediator.unregister(code, handler)
            except Exception:
                pass
