from PySide6.QtCore import Slot
from airunner.windows.installer.templates.confirmation_page_ui import Ui_confirmation_page
from airunner.windows.setup_wizard.base_wizard import BaseWizard


class ConfirmationPage(BaseWizard):
    class_name_ = Ui_confirmation_page

    def __init__(self, *args):
        super(ConfirmationPage, self).__init__(*args)

        checkboxes = [
            "compile_with_pyinstaller_checkbox",
            "download_ai_runner_checkbox",
            "download_sd_checkbox",
            "download_controlnet_checkbox",
            "download_llm_checkbox",
            "download_tts_checkbox",
            "download_stt_checkbox",
        ]

        for checkbox in checkboxes:
            element = getattr(self.ui, checkbox)
            element.blockSignals(True)
            element.setChecked(
                self.download_settings[checkbox]
            )
            element.blockSignals(False)

    @Slot(bool)
    def toggle_all_required(self, val: bool):
        items = self.ui.required_libraries.layout().count()
        for i in range(items):
            item = self.ui.required_libraries.layout().itemAt(i)
            item.widget().setChecked(val)

    @property
    def download_settings(self):
        return self.wizard().download_settings

    @Slot(bool)
    def toggle_download_ai_runner(self, val: bool):
        self.download_settings["download_ai_runner"] = val

    @Slot(bool)
    def toggle_download_sd(self, val: bool):
        self.download_settings["download_sd"] = val

    @Slot(bool)
    def toggle_download_controlnet(self, val: bool):
        self.download_settings["download_controlnet"] = val

    @Slot(bool)
    def toggle_download_llm(self, val: bool):
        self.download_settings["download_llm"] = val

    @Slot(bool)
    def toggle_download_tts(self, val: bool):
        self.download_settings["download_tts"] = val

    @Slot(bool)
    def toggle_download_stt(self, val: bool):
        self.download_settings["download_stt"] = val

    @Slot(bool)
    def toggle_compile_with_pyinstaller(self, val: bool):
        self.download_settings["compile_with_pyinstaller"] = val
