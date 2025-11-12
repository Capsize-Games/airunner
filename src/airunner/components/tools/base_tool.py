from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)


class BaseTool(
    MediatorMixin,
    SettingsMixin,
):
    def __init__(self, *args, **kwargs):
        super().__init__()
