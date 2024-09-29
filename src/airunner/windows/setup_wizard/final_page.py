from PySide6.QtWidgets import QVBoxLayout, QLabel
from airunner.windows.setup_wizard.base_wizard import BaseWizard


class FinalPage(BaseWizard):
    def initialize_form(self):
        self.setTitle("Setup Complete")
        layout = QVBoxLayout()
        label = QLabel("Setup is complete. Click Finish to close the wizard.")
        layout.addWidget(label)
        self.setLayout(layout)

    def save_settings(self):
        self.update_application_settings("run_setup_wizard", False)
