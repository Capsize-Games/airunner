from airunner.windows.setup_wizard.setup_wizard import DownloadWizard

from airunner.windows.setup_wizard.templates.vision_setup.download_vision_models_ui import Ui_vision_setup


class VisionSetup(DownloadWizard):
    class_name_ = Ui_vision_setup

    def __init__(self):
        super(VisionSetup, self).__init__()
        self.ui.lineEdit.setText(self.settings["ocr_settings"]["path"])

