from pathlib import Path

from airunner.components.downloader.gui.windows.setup_wizard.user_agreement.agreement_page import (
    AgreementPage,
)
from airunner.components.downloader.gui.windows.setup_wizard.user_agreement.templates.user_agreement_ui import (
    Ui_user_agreement,
)


class UserAgreement(AgreementPage):
    class_name_ = Ui_user_agreement
    setting_key = "user_agreement_checked"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._load_user_agreement_text()

    def _load_user_agreement_text(self):
        """Load the user agreement text from the markdown file."""
        agreement_file = Path(__file__).parent / "user_agreement_text.md"
        try:
            with open(agreement_file, "r", encoding="utf-8") as f:
                text = f.read()
            self.ui.label_2.setText(text)
        except FileNotFoundError:
            self.ui.label_2.setText(
                "Error: User agreement text file not found. "
                "Please contact support."
            )
