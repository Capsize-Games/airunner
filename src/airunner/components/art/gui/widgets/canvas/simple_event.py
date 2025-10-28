from typing import Any
from PySide6.QtCore import Qt


class SimpleEvent:
    """Simple event wrapper for events missing button attribute."""

    def __init__(self, original_event: Any) -> None:
        self.type_value = original_event.type()
        self.button_value = None
        self.buttons_value = Qt.MouseButton.NoButton

    def type(self) -> int:
        """Return the event type."""
        return self.type_value

    def button(self) -> None:
        """Return the button (always None for simple events)."""
        return self.button_value

    def buttons(self) -> Qt.MouseButton:
        """Return the button state (always NoButton for simple events)."""
        return self.buttons_value
