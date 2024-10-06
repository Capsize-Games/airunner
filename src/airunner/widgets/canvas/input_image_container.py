from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.canvas.templates.input_image_container_ui import Ui_input_image_container
from airunner.widgets.canvas.input_image import InputImage

class InputImageContainer(BaseWidget):
    widget_class_ = Ui_input_image_container

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_image = None

    def showEvent(self, event):
        if self.input_image is None:
            settings_key = self.settings_key
            self.input_image = InputImage(settings_key=self.settings_key)
            self.ui.tabWidget.addTab(self.input_image, "Input Image")
            label = "Image-to-Image"
            if settings_key == "controlnet_settings":
                label = "Controlnet"
                self.input_image = InputImage(settings_key=self.settings_key, use_generated_image=True)
                self.ui.tabWidget.addTab(self.input_image, "Generated Image")
            self.ui.label.setText(label)

    @property
    def settings_key(self):
        return self.property("settings_key")
