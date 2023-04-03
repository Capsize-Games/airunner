from airunner.windows.base_window import BaseWindow


class AboutWindow(BaseWindow):
    template_name = "about"
    window_title = "About AI Runner"

    def initialize_window(self):
        self.template.title.setText(f"AI Runner")
