from PySide6.QtWidgets import QWizard
from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin


class DownloadWizardWindow(
    QWizard,
    MediatorMixin,
    SettingsMixin
):
    """
    The download wizard window class for AI Runner.
    This class is used to download models and other resources required for AI Runner.
    """
    def __init__(self):
        """
        Initialize the download wizard window.
        """
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super(DownloadWizardWindow, self).__init__()

        self.setWindowTitle("AI Runner Download Wizard")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.IndependentPages, True)

        self.show()
