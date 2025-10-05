from PySide6.QtCore import Slot
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.settings.gui.widgets.document_preferences.templates.document_preferences_ui import (
    Ui_document_preferences,
)
from airunner.enums import SignalCode
from airunner.utils.settings import get_qsettings


class DocumentPreferencesWidget(BaseWidget):
    widget_class_ = Ui_document_preferences
    qsettings_group_name = "document_editor"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        settings = get_qsettings()
        settings.beginGroup(self.qsettings_group_name)
        autosave_enabled = settings.value("autosave_enabled", False, type=bool)
        self.ui.autosave_checkbox.blockSignals(True)
        self.ui.autosave_checkbox.setChecked(autosave_enabled)
        self.ui.autosave_checkbox.blockSignals(False)

    @Slot(bool)
    def on_autosave_checkbox_toggled(self, checked: bool):
        settings = get_qsettings()
        settings.beginGroup(self.qsettings_group_name)
        settings.setValue("autosave_enabled", checked)
        settings.endGroup()
        settings.sync()
        self.emit_signal(
            SignalCode.DOCUMENT_PREFERENCES_CHANGED,
            {"autosave_enabled": checked},
        )
