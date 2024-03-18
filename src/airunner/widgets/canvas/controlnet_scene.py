from PySide6.QtCore import Slot
from PySide6.QtWidgets import QFileDialog

from airunner.enums import SignalCode
from airunner.settings import VALID_IMAGE_FILES
from airunner.utils import convert_image_to_base64
from airunner.widgets.canvas.brush_scene import BrushScene


class ControlnetScene(BrushScene):
    settings_key = "controlnet_settings"

    def register_signals(self):
        signals = [
            (SignalCode.SD_CONTROLNET_IMAGE_GENERATED_SIGNAL, self.handle_controlnet_image_generated),
            (SignalCode.CONTROLNET_IMPORT_IMAGE_SIGNAL, self.import_image),
            (SignalCode.CONTROLNET_EXPORT_IMAGE_SIGNAL, self.export_image),
        ]
        for signal, handler in signals:
            self.register(signal, handler)

    @Slot(dict)
    def handle_controlnet_image_generated(self, message):
        settings = self.settings
        settings["controlnet_settings"]["image"] = convert_image_to_base64(message["image"])
        self.settings = settings
        self.refresh_image()

    def export_image(self, _message):
        image = self.current_active_image()
        if image:
            file_path, _ = QFileDialog.getSaveFileName(
                None,
                "Save Image",
                "",
                f"Image Files ({' '.join(VALID_IMAGE_FILES)})"
            )
            if file_path == "":
                return

            # If missing file extension, add it
            if not file_path.endswith(VALID_IMAGE_FILES):
                file_path = f"{file_path}.png"

            image.save(file_path)

    def import_image(self, _message):
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Open Image",
            "",
            f"Image Files ({' '.join(VALID_IMAGE_FILES)})"
        )
        if file_path == "":
            return
        self.load_image(file_path)
