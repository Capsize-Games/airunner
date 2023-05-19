from PIL.ImageFilter import Filter
from PIL import Image


class ColorBalanceFilter(Filter):
    name = "Color Balance"

    def __init__(self, cyan_red=0, magenta_green=0, yellow_blue=0):
        self.cyan_red = cyan_red
        self.magenta_green = magenta_green
        self.yellow_blue = yellow_blue

    def filter(self, image):
        red, green, blue, alpha = image.split()
        red = red.point(lambda i: i + (i * self.cyan_red))
        green = green.point(lambda i: i + (i * self.magenta_green))
        blue = blue.point(lambda i: i + (i * self.yellow_blue))
        image = Image.merge("RGBA", (red, green, blue, alpha))
        return image
