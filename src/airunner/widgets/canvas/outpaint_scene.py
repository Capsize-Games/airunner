from PySide6.QtWidgets import QFileDialog

from airunner.enums import SignalCode
from airunner.settings import VALID_IMAGE_FILES
from airunner.widgets.canvas.custom_scene import CustomScene


class OutpaintScene(CustomScene):
    settings_key = "outpaint_settings"

    def __init__(self, canvas_type: str):
        super().__init__(canvas_type)

    def register_signals(self):
        signals = [
            (SignalCode.OUTPAINT_COPY_IMAGE_SIGNAL, self.on_canvas_copy_image_signal),
            (SignalCode.OUTPAINT_CUT_IMAGE_SIGNAL, self.on_canvas_cut_image_signal),
            (SignalCode.OUTPAINT_ROTATE_90_CLOCKWISE_SIGNAL, self.on_canvas_rotate_90_clockwise_signal),
            (SignalCode.OUTPAINT_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL, self.on_canvas_rotate_90_counter_clockwise_signal),
            (SignalCode.OUTPAINT_PASTE_IMAGE_SIGNAL, self.on_paste_image_from_clipboard),
            (SignalCode.OUTPAINT_IMPORT_IMAGE_SIGNAL, self.import_image),
            (SignalCode.OUTPAINT_EXPORT_IMAGE_SIGNAL, self.export_image),
            (SignalCode.MASK_GENERATOR_WORKER_RESPONSE_SIGNAL, self.on_mask_generator_worker_response_signal),
        ]
        for signal, handler in signals:
            self.register(signal, handler)

    def on_mask_generator_worker_response_signal(self, message: dict):
        self.create_image(message["mask"])

    def import_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Open Image",
            "",
            f"Image Files ({' '.join(VALID_IMAGE_FILES)})"
        )
        if file_path == "":
            return
        self.load_image(file_path)
