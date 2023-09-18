from airunner.widgets.base_widget import BaseWidget


class FooterWidget(BaseWidget):
    name = "footer"

    def set_stylesheet(self):
        color = "#ffffff" if \
            self.app.settings_manager.dark_mode_enabled else "#000000"
        self.status_label.setStyleSheet(f"color: {color};")
        self.widget.setStyleSheet(self.app.css("footer_widget"))
