from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.canvas.templates.input_image_container_ui import Ui_input_image_container
from airunner.widgets.canvas.input_image import InputImage

class InputImageContainer(BaseWidget):
    widget_class_ = Ui_input_image_container

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register(SignalCode.MASK_GENERATOR_WORKER_RESPONSE_SIGNAL, self.on_mask_generator_worker_response_signal)
        self.register(SignalCode.MASK_UPDATED, self.on_mask_generator_worker_response_signal)
        self.register(SignalCode.CANVAS_IMAGE_UPDATED_SIGNAL, self.on_load_image_from_grid_signal)
        self.input_image = None
        self.generated_image = None

    def on_mask_generator_worker_response_signal(self, message):
        if self.input_image:
            self.input_image.on_mask_generator_worker_response_signal()

    def on_load_image_from_grid_signal(self):
        if self.input_image:
            self.input_image.load_image_from_grid()

    def showEvent(self, event):
        if self.input_image is None:
            settings_key = self.settings_key
            self.input_image = InputImage(settings_key=self.settings_key)
            self.ui.tabWidget.addTab(self.input_image, "Input Image")
            label = "Image-to-Image"
            if settings_key == "controlnet_settings":
                label = "Controlnet"
                self.generated_image = InputImage(settings_key=self.settings_key, use_generated_image=True)
                self.ui.tabWidget.addTab(self.generated_image, "Generated Image")
            elif settings_key == "outpaint_settings":
                label = "Inpaint / Outpaint"
            self.ui.label.setText(label)

    @property
    def settings_key(self):
        return self.property("settings_key")
