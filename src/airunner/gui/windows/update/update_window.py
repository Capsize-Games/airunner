from airunner.gui.windows.about.templates.about_ui import Ui_about_window
from airunner.gui.windows.base_window import BaseWindow
# open the version file from the root of the project and get the VERSION variable string from it


class UpdateWindow(BaseWindow):
    template_class_ = Ui_about_window

    def initialize_window(self):
        current_text = self.template.current_version_label.text()
        latest_text = self.template.latest_version_label.text()
        self.template.current_version_label.setText(f"{current_text} {self.application_settings.app_version}")
        self.template.latest_version_label.setText(f"{latest_text} {self.application_settings.app_version}")
