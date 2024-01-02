from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.image_generator_preferences.templates.image_generator_preferences_ui import Ui_image_generator_preferences


class ImageGeneratorPreferencesWidget(BaseWidget):
    widget_class_ = Ui_image_generator_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.stablediffusion.setChecked(self.settings_manager.current_image_generator == "stablediffusion")
    
    def stablediffusion_toggled(self, val):
        if val:
            self.settings_manager.set_value("current_image_generator", "stablediffusion")
            self.settings_manager.set_value("current_tab", "stablediffusion")
            self.settings_manager.set_value("current_section_stablediffusion", "txt2img")
            self.app.generator_tab_widget.set_current_section_tab()
            self.settings_manager.set_value("generator_section", "txt2img")