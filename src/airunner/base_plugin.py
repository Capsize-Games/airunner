from PySide6.QtWidgets import QWidget
from abc import ABC, abstractmethod


class BasePlugin(ABC):
    name: str = ""

    @abstractmethod
    def get_widget(self) -> QWidget:
        pass