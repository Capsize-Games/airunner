from PySide6.QtWidgets import QWidget
from abc import ABC, abstractmethod


class BasePlugin(ABC):
    name: str = ""

    @abstractmethod
    def get_widget(self) -> QWidget:
        """
        Get the widget for the plugin.

        Returns:
            QWidget: The widget for the plugin.
        """