from airunner.widgets.base_widget import BaseWidget


class FooterWidget(BaseWidget):
    name = "footer"

    def set_stylesheet(self):
        color = "#ffffff" if \
            self.settings_manager.settings.dark_mode_enabled.get() else "#000000"
        self.status_label.setStyleSheet(f"color: {color}; padding-top: 5px; padding-bottom: 5px; padding-left: 5px;")
        self.canvas_position.setStyleSheet(f"color: {color}; padding-top: 5px; padding-bottom: 5px;")
        self.widget.setStyleSheet(f"""
            border-top: 1px solid #121212;
            border-radius: 0px;
        """)
