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
            image_position_x = 0
            image_position_y = 0
            image_width = image.width
            image_height = image.height

            # Calculate the overlap between the active rectangle and the image
            active_rect = self.active_rect
            overlap_left = max(0, active_rect.left())
            overlap_right = min(self.settings["working_width"], active_rect.right())
            overlap_top = max(0, active_rect.top())
            overlap_bottom = min(self.settings["working_height"], active_rect.bottom())

            # If there is an overlap, draw a black rectangle on the mask at the overlap position
            left = active_rect.left()
            right = self.settings["working_width"]
            top = active_rect.top()
            bottom = self.settings["working_height"]

            # Create a white image of the same size as the input image
            mask = Image.new('RGB', (self.settings["working_width"], self.settings["working_height"]), 'black')
            draw = ImageDraw.Draw(mask)

            white_rectangle = (0, 0, right, bottom)
            black_rectangle = (0, 0, right, bottom)

            if left > 0:
                if overlap_left < overlap_right or overlap_top < overlap_bottom:
                    white_rectangle = (0, 0, right, bottom)
                elif overlap_right < overlap_left:
                    white_rectangle = (0, 0, overlap_right, bottom)
            elif left < 0:
                if overlap_left < overlap_right or overlap_top < overlap_bottom:
                    white_rectangle = (0, top, abs(left), bottom)
                elif overlap_right < overlap_left:
                    white_rectangle = (overlap_left, top, right, bottom)

            if top > 0:
                if overlap_left < overlap_right or overlap_top < overlap_bottom:
                    white_rectangle = (0, 0, right, bottom)
                elif overlap_bottom < overlap_top:
                    white_rectangle = (0, 0, right, overlap_bottom)
            elif top < 0:
                if overlap_left < overlap_right or overlap_top < overlap_bottom:
                    white_rectangle = (0, 0, right, abs(top))
                elif overlap_bottom < overlap_top:
                    white_rectangle = (0, overlap_top, right, bottom)

            if left > 0:
                if abs(left) < image_width:
                    black_rectangle = (
                        image_position_x,
                        image_position_y,
                        image_width - left,
                        image_height - top
                    )
                elif abs(left) > image_width:
                    black_rectangle = (
                        image_position_x,
                        image_position_y,
                        left - image_width,
                        top - image_height
                    )
            elif left < 0:
                if left < image_width:
                    black_rectangle = (
                        abs(left),
                        image_position_y,
                        image_width,
                        image_height - top
                    )
                elif left > image_width:
                    black_rectangle = (
                        image_position_x,
                        image_position_y,
                        left - image_width,
                        top - image_height
                    )

            if top > 0:
                if abs(top) < image_height:
                    black_rectangle = (
                        image_position_x,
                        image_position_y,
                        image_width - left,
                        image_height - top
                    )
                elif abs(top) > image_height:
                    black_rectangle = (
                        image_position_x,
                        image_position_y,
                        left - image_width,
                        top - image_height
                    )
            elif top < 0:
                if top < image_height:
                    black_rectangle = (
                        image_position_x,
                        abs(top),
                        image_width - left,
                        image_height
                    )
                elif top > image_height:
                    black_rectangle = (
                        image_position_x,
                        image_position_y,
                        left - image_width,
                        top - image_height
                    )

            draw.rectangle(white_rectangle, fill='white')
            draw.rectangle(black_rectangle, fill='black')
            return mask
        return None
