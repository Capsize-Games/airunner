from PySide6.QtCore import Slot
from airunner.gui.windows.setup_wizard.base_wizard import BaseWizard
from airunner.gui.windows.setup_wizard.model_setup.stable_diffusion_setup.templates.choose_model_ui import Ui_choose_model
from airunner.enums import StableDiffusionVersion, ImageGenerator
from airunner.data.bootstrap.model_bootstrap_data import model_bootstrap_data


class ChooseModel(BaseWizard):
    class_name_ = Ui_choose_model

    def __init__(self, *args):
        super(ChooseModel, self).__init__(*args)
        self.model_version: str = ""
        self.model: str = ""
        self.custom_model: str = ""
        self.using_custom_model = False

        # Hide the tab bar
        self.ui.tabWidget.tabBar().setVisible(False)

        # Iterate over StableDiffusionVersion enum
        for index, version in enumerate(StableDiffusionVersion):
            self.ui.versions.addItem(
                version.value,
                version
            )

        self.initialize_models()

    def initialize_models(self):
        self.ui.models.clear()
        for model in model_bootstrap_data:
            if (
                model["category"] == ImageGenerator.STABLEDIFFUSION.value and
                model["version"] == self.model_version and
                model["pipeline_action"] == "txt2img"
            ):
                self.ui.models.addItem(
                    model["name"],
                    model
                )

    @Slot(str)
    def model_version_changed(self, txt: str):
        self.model_version = txt
        self.initialize_models()

    @Slot(str)
    def custom_model_changed(self, txt: str):
        self.custom_model = txt

    @Slot(str)
    def model_changed(self, txt: str):
        self.model = txt

    @Slot(str)
    def custom_model_changed(self, val: str):
        pass

    @Slot(bool)
    def custom_model_toggled(self, _val: bool):
        self.using_custom_model = bool
        self.ui.tabWidget.setCurrentIndex(1)

    @Slot(bool)
    def model_type_toggled(self, _val: bool):
        self.using_custom_model = not bool
        self.ui.tabWidget.setCurrentIndex(0)
