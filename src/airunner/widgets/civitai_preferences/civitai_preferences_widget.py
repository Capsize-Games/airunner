from PySide6.QtCore import Slot, QTimer
from PySide6.QtWidgets import QLineEdit

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.civitai_preferences.templates.civitai_preferences_widget_ui import Ui_civitai_preferences


class CivitAIPreferencesWidget(BaseWidget):
    widget_class_ = Ui_civitai_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui.api_key.blockSignals(True)
        self.ui.api_key.setEchoMode(QLineEdit.EchoMode.Password)  # Set echo mode to Password
        self.ui.api_key.setText(self.settings.get('civitai_api_key', ''))
        self.ui.api_key.blockSignals(False)

        self.timer = QTimer()  # Create a QTimer instance
        self.timer.timeout.connect(self.save_settings)  # Connect the timer's timeout signal to the save_settings slot
        self.timer.setInterval(500)
        self._uncommitted_settings = None

    @Slot(str)
    def on_text_changed(self, text):
        if self._uncommitted_settings is None:
            settings = self.settings
        else:
            settings = self._uncommitted_settings
        settings['civitai_api_key'] = text
        self.timer.start()  # Start the timer when the text changes
        self._uncommitted_settings = settings

    @Slot()
    def save_settings(self):
        self.timer.stop()  # Stop the timer
        self.settings = self._uncommitted_settings
        self._uncommitted_settings = None
