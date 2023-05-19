from PIL import ImageEnhance
from PIL.ImageFilter import Filter


class SaturationFilter(Filter):
    name = "Saturation"

    def __init__(self, factor=1.0):
        self.factor = factor

    def filter(self, image):
        # limit self.factor to 2 decimal places
        self.factor = round(self.factor, 2)
        return ImageEnhance.Color(image).enhance(self.factor)
