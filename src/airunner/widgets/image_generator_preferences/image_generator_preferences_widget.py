from airunner.enums import ImageGenerator, GeneratorSection
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.image_generator_preferences.templates.image_generator_preferences_ui import Ui_image_generator_preferences


class ImageGeneratorPreferencesWidget(BaseWidget):
    widget_class_ = Ui_image_generator_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.initialize_categories()
        self.initialize_pipeline()
        self.initialize_action()

    def initialize_categories(self):
        self.ui.category.blockSignals(True)
        self.ui.category.clear()
        for item in ImageGenerator:
            self.ui.category.addItem(item.value)
        self.ui.category.setCurrentText(self.settings["current_image_generator"])
        self.ui.category.blockSignals(False)

    def initialize_pipeline(self):
        self.ui.pipeline.blockSignals(True)
        self.ui.pipeline.clear()
        for item in ImageGenerator:
            self.ui.pipeline.addItem(item.value)
        self.ui.pipeline.setCurrentText(self.settings["current_image_generator"])
        self.ui.pipeline.blockSignals(False)

    def initialize_action(self):
        self.ui.action.blockSignals(True)
        self.ui.action.clear()
        for item in GeneratorSection:
            self.ui.action.addItem(item.value)
        self.ui.action.setCurrentText(self.settings["current_image_generator"])
        self.ui.action.blockSignals(False)
    def stablediffusion_toggled(self, val):
        if val:
            settings = self.settings
            settings["current_image_generator"] = ImageGenerator.STABLEDIFFUSION.value
            settings["generator_section"] = GeneratorSection.TXT2IMG.value
            self.settings = settings

    def category_changed(self, val):
        settings = self.settings
        settings["generator_section"] = val
        self.settings = settings

    def pipeline_changed(self, val):
        settings = self.settings
        settings["current_image_generator"] = val
        self.settings = settings

    def version_changed(self, val):
        settings = self.settings
        settings["current_image_generator"] = val
        self.settings = settings

    def action_changed(self, val):
        settings = self.settings
        settings["current_image_generator"] = val
        self.settings = settings

    def model_changed(self, val):
        settings = self.settings
        settings["current_image_generator"] = val
        self.settings = settings

