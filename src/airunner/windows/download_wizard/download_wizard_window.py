from PySide6.QtWidgets import QWizard
from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.windows.setup_wizard.installation_settings.install_failed_page import InstallFailedPage
from airunner.windows.setup_wizard.installation_settings.install_page import InstallPage
from airunner.windows.setup_wizard.installation_settings.install_success_page import InstallSuccessPage
from airunner.windows.setup_wizard.path_settings.path_settings import PathSettings


class DownloadWizardWindow(QWizard, MediatorMixin, SettingsMixin):
    """
    The download wizard window class for AI Runner.
    This class is used to download models and other resources required for AI Runner.
    """
    def __init__(self):
        """
        Initialize the download wizard window.
        :param setup_settings: The setup settings dictionary.
        """
        MediatorMixin.__init__(self)
        
        super(DownloadWizardWindow, self).__init__()
        self.setWindowTitle("AI Runner Download Wizard")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.IndependentPages, True)

        self.button(
            QWizard.WizardButton.FinishButton
        ).clicked.connect(self.save_settings)

        self.button(QWizard.WizardButton.NextButton).clicked.connect(self.next_button_clicked)

        self.init_pages()

    def save_settings(self):
        """
        Override this function to save settings based on specific page in question.
        Do not call this function directly.
        :return:
        """
        self.update_application_settings("run_setup_wizard", False)
        self.update_application_settings("download_wizard_completed", True)

    def next_button_clicked(self):
        current_page = self.currentPage()
        if hasattr(current_page, 'next'):
            current_page.next()
        if hasattr(current_page, "start"):
            current_page.start()

    def init_pages(self):
        """
        Initialize the wizard pages based on setup settings.
        """
        failed = True

        if (
            self.application_settings.user_agreement_checked and
            self.application_settings.stable_diffusion_agreement_checked and
            self.application_settings.airunner_agreement_checked
        ):
            self.setPage(0, PathSettings(self))
            self.setPage(1, InstallPage(self))
            self.setPage(2, InstallSuccessPage(self))
            failed = False

        if failed:
            self.setPage(2, InstallFailedPage(self))

    def show_final_page(self):
        """
        Show the final page.
        """
        # Find the ID of the InstallSuccessPage
        for page_id in self.pageIds():
            page = self.page(page_id)
            if isinstance(page, InstallSuccessPage):
                self.setCurrentId(page_id)
                return
