from airunner.enums import SignalCode
from airunner.utils import convert_image_to_base64
from airunner.widgets.canvas.brush_scene import BrushScene


class ControlnetScene(BrushScene):
    settings_key = "controlnet_settings"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register(
            SignalCode.SD_CONTROLNET_IMAGE_GENERATED_SIGNAL,
            self.handle_controlnet_image_generated
        )

    def handle_controlnet_image_generated(self, image):
        settings = self.settings
        settings["controlnet_settings"]["image"] = convert_image_to_base64(image)
        self.settings = settings
        self.refresh_image()
