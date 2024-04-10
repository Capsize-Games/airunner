from PySide6.QtWidgets import QVBoxLayout, QLabel
from airunner.windows.setup_wizard.base_wizard import BaseWizard


class WelcomePage(BaseWizard):
    def __init__(self):
        super(WelcomePage, self).__init__()

        self.setTitle("Welcome")
        layout = QVBoxLayout()
        label = QLabel("Welcome to the AI Runner setup wizard. Click Next to continue.")
        layout.addWidget(label)
        self.setLayout(layout)
