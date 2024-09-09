from airunner.filters.base_filter import BaseFilter
from PIL import ImageOps

class Invert(BaseFilter):
    def apply_filter(self, image, do_reset):
        # Ensure the image is in RGB mode
        image = image.convert("RGB")
        # Invert the colors
        return ImageOps.invert(image)
