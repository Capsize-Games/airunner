from PySide6.QtWidgets import QWizard
from airunner.mediator_mixin import MediatorMixin
from airunner.utils.os_utils.create_airunner_directory import create_airunner_paths
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.windows.setup_wizard.installation_settings.install_failed_page import InstallFailedPage
from airunner.windows.setup_wizard.installation_settings.install_page import InstallPage
from airunner.windows.setup_wizard.installation_settings.install_success_page import InstallSuccessPage


class DownloadWizardWindow(
    QWizard,
    MediatorMixin,
    SettingsMixin
):
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
        failed = True

        if (
            setup_settings["user_agreement_completed"] and
            setup_settings["airunner_license_completed"]
        ):
            self.construct_paths(self.settings["path_settings"]["base_path"])
            create_airunner_paths(self.settings["path_settings"])

            self.enable_sd = setup_settings["enable_sd"]
            self.enable_controlnet = setup_settings["enable_controlnet"]

            if not self.enable_sd or self.enable_sd and setup_settings["sd_license_completed"]:

                self.enable_llm = setup_settings["enable_llm"]
                self.enable_tts = setup_settings["enable_tts"]
                self.enable_stt = setup_settings["enable_stt"]

                self.setWindowTitle("AI Runner Download Wizard")
                self.setWizardStyle(QWizard.ModernStyle)
                self.setOption(QWizard.IndependentPages, True)

                self.addPage(InstallPage(self, setup_settings))
                self.addPage(InstallSuccessPage(self))
                failed = False
                self.show()

        if failed:
            self.addPage(
                InstallFailedPage(self)
            )
