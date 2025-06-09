from PySide6.QtCore import Slot
from airunner.enums import SignalCode, TemplateName
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.theme_settings.templates.theme_settings_ui import (
    Ui_theme_settings,
)
from airunner.utils.settings import get_qsettings


class ThemeSettingsWidget(BaseWidget):
    widget_class_ = Ui_theme_settings

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.theme_combobox.addItems([e.value for e in TemplateName])
        qsettings = get_qsettings()
        theme = qsettings.value("theme", "System Default")
        self.ui.theme_combobox.setCurrentText(theme)

    @Slot(str)
    def on_theme_combobox_currentTextChanged(self, val: str):
        """
        Slot to handle theme changes from the combobox.
        """
        template = TemplateName(val)
        settings = get_qsettings()
        settings.setValue("theme", val)
        self.api.refresh_stylesheet(template)

        # self.api.send_signal(SignalCode.THEME_CHANGED, {"template": template})
