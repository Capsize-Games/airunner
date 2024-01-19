from airunner.windows.about.templates.about_ui import Ui_about_window
from airunner.windows.base_window import BaseWindow
# open the version file from the root of the project and get the VERSION variable string from it


class AboutWindow(BaseWindow):
    template_class_ = Ui_about_window

    def initialize_window(self):
        self.ui.title.setText(f"AI Runner {self.settings['app_version']}")
