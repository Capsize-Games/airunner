from airunner.windows.setup_wizard.setup_wizard_window import DownloadWizard

from airunner.windows.setup_wizard.model_setup.vision_setup import Ui_vision_setup


class VisionSetup(DownloadWizard):
    class_name_ = Ui_vision_setup

    def __init__(self):
        super(VisionSetup, self).__init__()
        self.ui.lineEdit.setText(self.settings["ocr_settings"]["path"])

