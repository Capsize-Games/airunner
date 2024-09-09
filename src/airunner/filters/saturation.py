from PIL import ImageEnhance
from airunner.filters.base_filter import BaseFilter


class SaturationFilter(BaseFilter):
    def apply_filter(self, image, do_reset):
        # Transform self.factor from [0, 100] to [-1, 2]
        factor = (self.factor - 50) / 25 + 1
        # Limit self.factor to 2 decimal places
        factor = round(factor, 2)
        return ImageEnhance.Color(image).enhance(factor)
