from PIL import Image, ImageDraw
from PySide6.QtCore import QRect
from airunner.enums import SignalCode
from airunner.utils.convert_base64_to_image import convert_base64_to_image
from airunner.workers.worker import Worker


class MaskGeneratorWorker(Worker):
    @property
    def active_rect(self):
        settings = self.settings
        rect = QRect(
            settings["active_grid_settings"]["pos_x"],
            settings["active_grid_settings"]["pos_y"],
            settings["working_width"],
            settings["working_height"]
        )
        rect.translate(-settings["canvas_settings"]["pos_x"], -settings["canvas_settings"]["pos_y"])
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
        settings = self.settings
        image = convert_base64_to_image(settings["canvas_settings"]["image"])
        if image is not None:
            image_width = image.width
            image_height = image.height

            # Create a white image of the same size as the working area
            mask = Image.new('RGB', (settings["working_width"], settings["working_height"]), 'white')
            draw = ImageDraw.Draw(mask)

            # Calculate the position and size of the black rectangle (image)
            black_left = max(0, -self.active_rect.left())
            black_top = max(0, -self.active_rect.top())
            black_right = min(image_width, settings["working_width"] - self.active_rect.left())
            black_bottom = min(image_height, settings["working_height"] - self.active_rect.top())

            # Ensure the coordinates are valid
            if black_right >= black_left and black_bottom >= black_top:
                # Draw the black rectangle (image) on the mask
                draw.rectangle((black_left, black_top, black_right, black_bottom), fill='black')

            return mask
        return None
