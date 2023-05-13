from PIL import ImageEnhance
from PIL.ImageFilter import Filter


class SaturationFilter(Filter):
    name = "Saturation"

    def __init__(self, factor=1.0):
        self.factor = factor

    def filter(self, image):
        return ImageEnhance.Color(image).enhance(1.0 + self.factor)
