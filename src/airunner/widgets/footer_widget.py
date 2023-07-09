from airunner.widgets.base_widget import BaseWidget


class FooterWidget(BaseWidget):
    name = "footer"

    def set_stylesheet(self):
        color = "#ffffff" if \
            self.settings_manager.settings.dark_mode_enabled.get() else "#000000"
        self.status_label.setStyleSheet(f"color: {color};")
        self.widget.setStyleSheet(self.app.css("footer_widget"))
