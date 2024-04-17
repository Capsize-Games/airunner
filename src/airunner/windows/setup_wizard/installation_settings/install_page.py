import time
from PySide6.QtCore import QObject, QThread
from airunner.windows.setup_wizard.base_wizard import BaseWizard
from airunner.windows.setup_wizard.installation_settings.templates.install_page_ui import Ui_install_page


class InstallWorker(
    QObject
):
    def __init__(self, parent, setup_settings):
        super(InstallWorker, self).__init__()
        self.parent = parent
        self.setup_settings = setup_settings

    def run(self):
        if (
            self.setup_settings["user_agreement_completed"] and
            self.setup_settings["airunner_license_completed"]
        ):
            self.parent.set_status("Downloading models...")
            time.sleep(1)
            self.parent.update_progress_bar()

            if self.setup_settings["enable_sd"] and not self.setup_settings["sd_license_completed"]:
                self.parent.set_status("Downloading SD models...")
                time.sleep(1)
                self.parent.update_progress_bar()

                if self.setup_settings["enable_controlnet"]:
                    self.parent.set_status("Downloading ControlNet models...")
                    time.sleep(1)
                    self.parent.update_progress_bar()

            if self.setup_settings["enable_llm"]:
                self.parent.set_status("Downloading LLM models...")
                time.sleep(1)
                self.parent.update_progress_bar()

            if self.setup_settings["enable_tts"]:
                self.parent.set_status("Downloading TTS models...")
                time.sleep(1)
                self.parent.update_progress_bar()

            if self.setup_settings["enable_stt"]:
                self.parent.set_status("Downloading STT models...")
                time.sleep(1)
                self.parent.update_progress_bar()

            self.parent.set_status("Installation complete.")
            self.parent.update_progress_bar()


class InstallPage(BaseWizard):
    class_name_ = Ui_install_page

    def __init__(self, parent, setup_settings):
        super(InstallPage, self).__init__(parent)
        self.setup_settings = setup_settings

        # reset the progress bar
        self.ui.progress_bar.setValue(0)
        self.ui.progress_bar.setMaximum(100)

        self.total_steps = 6
        if not self.setup_settings["enable_sd"] or not self.setup_settings["sd_license_completed"]:
            self.total_steps -= 1
        if not self.setup_settings["enable_controlnet"]:
            self.total_steps -= 1
        if not self.setup_settings["enable_llm"]:
            self.total_steps -= 1
        if not self.setup_settings["enable_tts"]:
            self.total_steps -= 1
        if not self.setup_settings["enable_stt"]:
            self.total_steps -= 1

        self.thread = QThread()
        self.worker = InstallWorker(self, setup_settings)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def update_progress_bar(self):
        self.total_steps -= 1
        self.ui.progress_bar.setValue(100 / self.total_steps)

    def set_status(self, status):
        self.ui.status.setText(status)
