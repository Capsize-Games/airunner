from PIL import ImageEnhance
from PIL.ImageFilter import Filter


class ColorBalanceFilter(Filter):
    name = "Color Balance"

    def __init__(self, cyan_red=0, magenta_green=0, yellow_blue=0):
        self.cyan_red = cyan_red
        self.magenta_green = magenta_green
        self.yellow_blue = yellow_blue

    def filter(self, image):
        # Apply enhancement
        image = ImageEnhance.Color(image).enhance(1.0 + self.cyan_red)
        image = ImageEnhance.Color(image).enhance(1.0 + self.magenta_green)
        image = ImageEnhance.Color(image).enhance(1.0 + self.yellow_blue)
        return image
