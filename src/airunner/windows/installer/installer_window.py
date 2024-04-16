from PySide6.QtWidgets import QWizard
from airunner.mediator_mixin import MediatorMixin
from airunner.windows.installer.completion_page import CompletionPage
from airunner.windows.installer.confirmation_page import ConfirmationPage
from airunner.windows.installer.download_page import DownloadPage
from airunner.windows.main.settings_mixin import SettingsMixin


class InstallerWindow(
    QWizard,
    MediatorMixin,
    SettingsMixin
):
    def __init__(self, *args):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super(InstallerWindow, self).__init__(*args)

        self.page_ids = {}

        self.do_download_sd_models = True
        self.do_download_controlnet_models = True
        self.do_download_llm = True
        self.do_download_tts_models = True
        self.do_download_stt_models = True

        self.pages = {
            "confirmation_page": ConfirmationPage(self),
            "download_page": DownloadPage(self),
            "completion_page": CompletionPage(self),
        }

        for page_name, page in self.pages.items():
            self.addPage(page)

        self.setWindowTitle("AI Runner Setup Wizard")

    @property
    def download_settings(self):
        return {
            "compile_with_pyinstaller": False,
            "download_ai_runner": True,
            "download_sd": self.do_download_sd_models,
            "download_controlnet": self.do_download_controlnet_models,
            "download_llm": self.do_download_llm,
            "download_tts": self.do_download_tts_models,
            "download_stt": self.do_download_stt_models,
        }

    def addPage(self, page):
        page_id = super().addPage(page)
        self.page_ids[page] = page_id
        return page_id