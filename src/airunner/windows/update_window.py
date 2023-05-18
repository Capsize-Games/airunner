from airunner.windows.base_window import BaseWindow
# open the version file from the root of the project and get the VERSION variable string from it


class UpdateWindow(BaseWindow):
    template_name = "update"
    window_title = "Update AI Runner"

    def initialize_window(self):
        current_text = self.template.current_version_label.text()
        latest_text = self.template.latest_version_label.text()
        self.template.current_version_label.setText(f"{current_text} {self.app.version}")
        self.template.latest_version_label.setText(f"{latest_text} {self.app.latest_version}")
