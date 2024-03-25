from PIL import Image, ImageDraw
from PySide6.QtCore import QRect

from airunner.enums import SignalCode
from airunner.utils import convert_base64_to_image
from airunner.workers.worker import Worker


class MaskGeneratorWorker(Worker):
    @property
    def active_rect(self):
        rect = QRect(
            self.settings["active_grid_settings"]["pos_x"],
            self.settings["active_grid_settings"]["pos_y"],
            self.settings["active_grid_settings"]["width"],
            self.settings["active_grid_settings"]["height"]
        )
        rect.translate(-self.settings["canvas_settings"]["pos_x"], -self.settings["canvas_settings"]["pos_y"])
        return rect

    def register_signals(self):
        self.register(SignalCode.ACTIVE_GRID_AREA_MOVED_SIGNAL, self.on_active_grid_area_moved_signal)

    def on_active_grid_area_moved_signal(self, message: dict):
        mask = self.generate_mask()
        self.emit_signal(
            SignalCode.MASK_GENERATOR_WORKER_RESPONSE_SIGNAL,
            {"mask": mask}
        )

    def generate_mask(self) -> Image:
        image = convert_base64_to_image(self.settings["canvas_settings"]["image"])
        if image is not None:
            image_width = image.width
            image_height = image.height

            # Create a white image of the same size as the working area
            mask = Image.new('RGB', (self.settings["working_width"], self.settings["working_height"]), 'white')
            draw = ImageDraw.Draw(mask)

            # Calculate the position and size of the black rectangle (image)
            black_left = max(0, -self.active_rect.left())
            black_top = max(0, -self.active_rect.top())
            black_right = min(image_width, self.settings["working_width"] - self.active_rect.left())
            black_bottom = min(image_height, self.settings["working_height"] - self.active_rect.top())

            # Draw the black rectangle (image) on the mask
            draw.rectangle((black_left, black_top, black_right, black_bottom), fill='black')

            return mask
        return None
