from importlib.metadata import version

from airunner.windows.about.templates.about_ui import Ui_about_window
from airunner.windows.base_window import BaseWindow


class AboutWindow(BaseWindow):
    template_class_ = Ui_about_window

    def initialize_window(self):
        self.ui.title.setText(f"AI Runner v{version('airunner')}")
