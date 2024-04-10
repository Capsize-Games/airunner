from PySide6.QtWidgets import QVBoxLayout, QLabel
from airunner.windows.setup_wizard.base_wizard import BaseWizard


class FinalPage(BaseWizard):
    def __init__(self):
        super(FinalPage, self).__init__()

        self.setTitle("Setup Complete")
        layout = QVBoxLayout()
        label = QLabel("Setup is complete. Click Finish to close the wizard.")
        layout.addWidget(label)
        self.setLayout(layout)

        settings = self.settings
        settings["run_setup_wizard"] = False
        self.settings = settings
