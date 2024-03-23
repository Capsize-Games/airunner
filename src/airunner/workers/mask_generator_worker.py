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
        self.add_to_queue(message)

    def handle_message(self, message):
        mask = self.generate_mask()
        self.emit_signal(
            SignalCode.MASK_GENERATOR_WORKER_RESPONSE_SIGNAL,
            {"mask": mask}
        )

    def generate_mask(self) -> Image:
        image = convert_base64_to_image(self.settings["canvas_settings"]["image"])
        if image is not None:
            # Create a white image of the same size as the input image
            mask = Image.new('RGB', (self.settings["working_width"], self.settings["working_height"]), 'black')
            draw = ImageDraw.Draw(mask)

            # Calculate the overlap between the active rectangle and the image
            active_rect = self.active_rect
            image_overlap_left = max(0, active_rect.left())
            image_overlap_top = max(0, active_rect.top())
            image_overlap_right = min(self.settings["working_width"], active_rect.right())
            image_overlap_bottom = min(self.settings["working_height"], active_rect.bottom())

            overlap_left = max(0, active_rect.left())
            overlap_top = self.settings["working_height"] - active_rect.top()
            overlap_right = min(self.settings["working_width"], active_rect.right())
            overlap_bottom = self.settings["working_height"] + active_rect.top()

            # If there is an overlap, draw a black rectangle on the mask at the overlap position
            if overlap_left < overlap_right and overlap_top < overlap_bottom:
                draw.rectangle((overlap_left, overlap_top, overlap_right, overlap_bottom), fill='white')

                # Crop the image at the overlap position
                cropped_image = image.crop(
                    (image_overlap_left, image_overlap_top, image_overlap_right, image_overlap_bottom))

                # Create a new black image of the same size as the input image
                new_image = Image.new('RGB', (self.settings["working_width"], self.settings["working_height"]), 'black')

                # Paste the cropped image to the top of the new image
                new_image.paste(cropped_image, (0, 0))
            return mask
        return None
