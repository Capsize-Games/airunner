from typing import Optional

from airunner.components.application.gui.widgets.base_widget import BaseWidget


class BasePlugin:
    @property
    def name(self) -> str:
        raise NotImplementedError("Plugin name must be implemented")

    def get_widget(self) -> Optional[BaseWidget]:
        """
        Returns a widget that can be used in the UI.
        This method should be implemented by subclasses.
        """
        raise NotImplementedError("Plugin widget must be implemented")
