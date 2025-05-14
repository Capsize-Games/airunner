from PySide6.QtWidgets import QWizard
from PySide6.QtCore import QTimer
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin
from airunner.gui.windows.setup_wizard.installation_settings.install_failed_page import (
    InstallFailedPage,
)
from airunner.gui.windows.setup_wizard.installation_settings.choose_models_page import (
    ChooseModelsPage,
)
from airunner.gui.windows.setup_wizard.installation_settings.install_page import (
    InstallPage,
)
from airunner.gui.windows.setup_wizard.installation_settings.install_success_page import (
    InstallSuccessPage,
)
from airunner.gui.windows.setup_wizard.path_settings.path_settings import (
    PathSettings,
)


class DownloadWizardWindow(
    MediatorMixin,
    SettingsMixin,
    QWizard,
):
    """
    The download wizard window class for AI Runner.
    This class is used to download models and other resources required for AI Runner.
    """

    def __init__(self):
        """
        Initialize the download wizard window.
        :param setup_settings: The setup settings dictionary.
        """
        super().__init__()
        self.install_page = None
        self.setWindowTitle("AI Runner Download Wizard")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.IndependentPages, True)

        self.button(QWizard.WizardButton.FinishButton).clicked.connect(
            self.save_settings
        )

        self.button(QWizard.WizardButton.NextButton).clicked.connect(
            self.next_button_clicked
        )

        self.init_pages()

        # Connect signals for Next and Back buttons to control their state
        self.currentIdChanged.connect(self.on_page_changed)

        # We'll disable the next button immediately if we're on the installation page
        self.disableNextIfInstallPage()

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
        if hasattr(current_page, "next"):
            current_page.next()
        if hasattr(current_page, "start"):
            current_page.start()

    def init_pages(self):
        """
        Initialize the wizard pages based on setup settings.
        """
        failed = True

        if (
            self.application_settings.user_agreement_checked
            and self.application_settings.stable_diffusion_agreement_checked
            and self.application_settings.airunner_agreement_checked
        ):
            self.setPage(0, PathSettings(self))
            choose_models_page = ChooseModelsPage(self)
            self.setPage(1, choose_models_page)
            self.install_page = InstallPage(
                self,
                stablediffusion_models=choose_models_page.models,
                models_enabled=choose_models_page.models_enabled,
            )
            self.setPage(2, self.install_page)
            self.setPage(3, InstallSuccessPage(self))
            failed = False

        if failed:
            self.setPage(1, InstallFailedPage(self))

    def on_page_changed(self, id):
        """Handle page changes to properly manage button states"""
        # If we're now on the install page, disable the next button
        if self.currentPage() == self.install_page:
            self.disableNextButton()

            # Start the installation process which will re-enable the button when done
            if self.install_page:
                QTimer.singleShot(100, self.install_page.start)

    def disableNextIfInstallPage(self):
        """Check if current page is install page and disable Next button if so"""
        if (
            hasattr(self, "install_page")
            and self.currentPage() == self.install_page
        ):
            self.disableNextButton()

    def disableNextButton(self):
        """Disable the Next button"""
        if self.button(QWizard.WizardButton.NextButton):
            self.button(QWizard.WizardButton.NextButton).setEnabled(False)

    def show_final_page(self):
        """
        Show the final page.
        """
        # Find the ID of the InstallSuccessPage
        for page_id in self.pageIds():
            page = self.page(page_id)
            if isinstance(page, InstallSuccessPage):
                self.setCurrentId(page_id)
                # Don't call next() on previous_page as it doesn't exist
                # Instead, just update the wizard's UI state
                self.button(QWizard.WizardButton.BackButton).setEnabled(
                    False
                )  # Disable back button
                self.button(QWizard.WizardButton.NextButton).setEnabled(
                    False
                )  # Disable next button
                self.button(QWizard.WizardButton.FinishButton).setEnabled(
                    True
                )  # Enable finish button
                return
