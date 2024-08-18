from PySide6.QtWidgets import QWizard
from airunner.mediator_mixin import MediatorMixin
from airunner.utils.os.create_airunner_directory import create_airunner_paths
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.windows.setup_wizard.installation_settings.install_failed_page import InstallFailedPage
from airunner.windows.setup_wizard.installation_settings.install_page import InstallPage
from airunner.windows.setup_wizard.installation_settings.install_success_page import InstallSuccessPage

class DownloadWizardWindow(QWizard, MediatorMixin, SettingsMixin):
    """
    The download wizard window class for AI Runner.
    This class is used to download models and other resources required for AI Runner.
    """
    def __init__(self, setup_settings: dict):
        """
        Initialize the download wizard window.
        :param setup_settings: The setup settings dictionary.
        """
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super(DownloadWizardWindow, self).__init__()

        self.setup_settings = setup_settings

        self.setWindowTitle("AI Runner Download Wizard")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.IndependentPages, True)

        self.init_pages()

    def init_pages(self):
        """
        Initialize the wizard pages based on setup settings.
        """
        failed = True

        if (
            self.setup_settings["user_agreement_completed"] and
            self.setup_settings["airunner_license_completed"] and
            self.setup_settings["llama_license_completed"]
        ):
            self.construct_paths(self.settings["path_settings"]["base_path"])
            create_airunner_paths(self.settings["path_settings"])

            self.enable_sd = self.setup_settings["enable_sd"]
            self.enable_controlnet = self.setup_settings["enable_controlnet"]

            if not self.enable_sd or (self.enable_sd and self.setup_settings["sd_license_completed"]):
                self.enable_llm = self.setup_settings["enable_llm"]
                self.enable_tts = self.setup_settings["enable_tts"]
                self.enable_stt = self.setup_settings["enable_stt"]

                self.setPage(1, InstallSuccessPage(self))
                self.setPage(0, InstallPage(self, self.setup_settings))
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
