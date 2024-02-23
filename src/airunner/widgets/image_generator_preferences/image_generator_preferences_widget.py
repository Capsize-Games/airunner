from airunner.enums import ImageGenerator, GeneratorSection
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.image_generator_preferences.templates.image_generator_preferences_ui import Ui_image_generator_preferences


class ImageGeneratorPreferencesWidget(BaseWidget):
    widget_class_ = Ui_image_generator_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def stablediffusion_toggled(self, val):
        if val:
            settings = self.settings
            settings["current_image_generator"] = ImageGenerator.STABLEDIFFUSION.value
            settings["generator_section"] = GeneratorSection.TXT2IMG.value
            self.settings = settings
