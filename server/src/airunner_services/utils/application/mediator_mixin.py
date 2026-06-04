"""Mixin helpers for classes that emit and receive mediated signals."""

from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from airunner_services.utils.application.signal_mediator import SignalMediator


class MediatorMixin:
    """Use with classes that need to emit and receive shared signals."""

    _signal_handlers: dict[object, Callable] = {}

    def __init__(
        self,
        mediator: Optional[SignalMediator] = None,
        message_backend: Optional[dict] = None,
        *args,
        **kwargs,
    ) -> None:
        del message_backend
        if type(mediator) is not SignalMediator:
            mediator = None

        self.mediator = mediator or SignalMediator()

        super().__init__(*args, **kwargs)
        self.register_signals()

        try:
            if hasattr(self, "destroyed"):
                self.destroyed.connect(lambda: self.unregister_signals())
        except Exception:
            pass

    @property
    def signal_handlers(self) -> dict[object, Callable]:
        """Return the handlers registered for this instance."""
        return self._signal_handlers

    @signal_handlers.setter
    def signal_handlers(self, value: dict[object, Callable]) -> None:
        self._signal_handlers = value

    def register_signals(self) -> None:
        """Register all handlers exposed by the instance mapping."""
        for signal, handler in self.signal_handlers.items():
            self.register(signal, handler)

    def emit_signal(self, code: object, data: object = None) -> None:
        """Emit one mediated signal payload."""
        self.mediator.emit_signal(code, data)

    def register(self, code: object, slot_function: Callable) -> None:
        """Register one callback for one signal key."""
        self.mediator.register(code, slot_function)

    def unregister(self, code: object, slot_function: Callable) -> None:
        """Unregister one previously registered callback."""
        self.mediator.unregister(code, slot_function)

    def unregister_signals(self) -> None:
        """Unregister all handlers that belong to this instance."""
        for code, handler in list(self.signal_handlers.items()):
            try:
                self.mediator.unregister(code, handler)
            except Exception:
                pass


__all__ = ["MediatorMixin"]
