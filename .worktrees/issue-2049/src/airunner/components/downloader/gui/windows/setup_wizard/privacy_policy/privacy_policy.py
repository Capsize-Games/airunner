from PySide6.QtCore import Slot

from airunner.components.downloader.gui.windows.setup_wizard.base_wizard import BaseWizard
from airunner.components.downloader.gui.windows.setup_wizard.privacy_policy.templates.privacy_policy_ui import (
    Ui_privacy_policy,
)


class PrivacyPolicy(BaseWizard):
    class_name_ = Ui_privacy_policy
    setting_key = "privacy_policy_checked"

    def __init__(self, *args):
        super(PrivacyPolicy, self).__init__(*args)
        self.agreed = False

        # Force refresh of isComplete status when initialized
        self.completeChanged.emit()

    @Slot(bool)
    def agreement_clicked(self, val):
        self.agreed = val

        # Emit signal to update Next button state
        self.completeChanged.emit()

    def isComplete(self):
        """
        Control whether the Next button is enabled based on checkbox state.
        Returns True only if the agreement checkbox has been checked.
        """
        return self.agreed
