from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.image_generator_preferences.templates.image_generator_preferences_ui import Ui_image_generator_preferences


class ImageGeneratorPreferencesWidget(BaseWidget):
    widget_class_ = Ui_image_generator_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def stablediffusion_toggled(self, val):
        if val:
            settings = self.settings
            settings["current_image_generator"] = "stablediffusion"
            self.settings = settings
            settings = self.settings
            settings["generator_section"] = "txt2img"
            self.settings = settings