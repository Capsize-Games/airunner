from PySide6.QtCore import Slot
from PySide6.QtWidgets import QFileDialog

from airunner.enums import SignalCode
from airunner.settings import VALID_IMAGE_FILES
from airunner.utils import convert_image_to_base64
from airunner.widgets.canvas.brush_scene import BrushScene


class ControlnetScene(BrushScene):
    settings_key = "controlnet_settings"

    def __init__(self, canvas_type: str):
        super().__init__(canvas_type)

    def register_signals(self):
        signals = [
            (SignalCode.CONTROLNET_COPY_IMAGE_SIGNAL, self.on_canvas_copy_image_signal),
            (SignalCode.CONTROLNET_CUT_IMAGE_SIGNAL, self.on_canvas_cut_image_signal),
            (SignalCode.CANVAS_ROTATE_90_CLOCKWISE_SIGNAL, self.on_canvas_rotate_90_clockwise_signal),
            (SignalCode.CANVAS_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL, self.on_canvas_rotate_90_counter_clockwise_signal),
            (SignalCode.CONTROLNET_PASTE_IMAGE_SIGNAL, self.paste_image_from_clipboard),
            (SignalCode.CONTROLNET_EXPORT_IMAGE_SIGNAL, self.export_image),
            (SignalCode.CONTROLNET_IMPORT_IMAGE_SIGNAL, self.import_image),
            (SignalCode.SD_CONTROLNET_IMAGE_GENERATED_SIGNAL, self.handle_controlnet_image_generated),
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
