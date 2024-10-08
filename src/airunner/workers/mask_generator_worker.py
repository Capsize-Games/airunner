import numpy as np
from PIL import Image, ImageDraw
from PySide6.QtCore import QRect
from airunner.enums import SignalCode
from airunner.utils.convert_base64_to_image import convert_base64_to_image
from airunner.workers.worker import Worker


class MaskGeneratorWorker(Worker):
    @property
    def active_rect(self):
        rect = QRect(
            self.active_grid_settings.pos_x,
            self.active_grid_settings.pos_y,
            self.application_settings.working_width,
            self.application_settings.working_height
        )
        rect.translate(-self.drawing_pad_settings.x_pos, -self.drawing_pad_settings.y_pos)
        return rect

    def register_signals(self):
        self.register(SignalCode.GENERATE_MASK, self.on_generate_mask_signal)

    def on_generate_mask_signal(self, message: dict):
        mask = self.generate_mask()
        self.emit_signal(
            SignalCode.MASK_GENERATOR_WORKER_RESPONSE_SIGNAL,
            {"mask": mask}
        )

    def generate_mask(self) -> Image:
        base_64_image = self.drawing_pad_settings.image
        if base_64_image is None:
            return
        image = convert_base64_to_image(base_64_image)
        image = image.convert('RGBA')
        if image is not None:
            image_width = image.width
            image_height = image.height

            # Create a white image of the same size as the working area
            mask = Image.new('RGB', (self.application_settings.working_width, self.application_settings.working_height),
                             'white')
            mask_data = np.array(mask)

            # Calculate the position and size of the black rectangle (image)
            black_left = max(0, -self.active_rect.left())
            black_top = max(0, -self.active_rect.top())
            black_right = min(image_width, self.application_settings.working_width - self.active_rect.left())
            black_bottom = min(image_height, self.application_settings.working_height - self.active_rect.top())

            # Ensure the coordinates are valid
            if black_right >= black_left and black_bottom >= black_top:
                # Draw the black rectangle (image) on the mask
                mask_data[black_top:black_bottom, black_left:black_right] = [0, 0, 0]

            # Check for transparent pixels and draw them as white on the mask
            if image.mode == 'RGBA':
                image_data = np.array(image)
                transparent_pixels = (image_data[:, :, 3] == 0)

                # Calculate the mask coordinates for transparent pixels
                mask_y, mask_x = np.where(transparent_pixels)  # Note the order of mask_x and mask_y
                mask_x -= self.active_rect.left()
                mask_y -= self.active_rect.top()

                # Ensure the coordinates are within the mask bounds
                valid_coords = (mask_x >= 0) & (mask_x < self.application_settings.working_width) & \
                               (mask_y >= 0) & (mask_y < self.application_settings.working_height)
                mask_x = mask_x[valid_coords]
                mask_y = mask_y[valid_coords]

                # Draw white pixels on the mask
                mask_data[mask_y, mask_x] = [255, 255, 255]

            # Convert the modified mask data back to an image
            mask = Image.fromarray(mask_data)
            return mask
        return None
