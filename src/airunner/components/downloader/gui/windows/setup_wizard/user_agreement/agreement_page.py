from PySide6.QtCore import Slot
from airunner.components.downloader.gui.windows.setup_wizard.base_wizard import BaseWizard


class AgreementPage(BaseWizard):
    setting_key = ""

    def __init__(self, *args):
        super(AgreementPage, self).__init__(*args)
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
