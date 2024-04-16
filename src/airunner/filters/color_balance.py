from PIL import Image
from airunner.filters.base_filter import BaseFilter


class ColorBalanceFilter(BaseFilter):
    def apply_filter(self, image, _do_reset):
        image = image.convert("RGBA")
        red, green, blue, alpha = image.split()
        red = red.point(lambda i: i + (i * self.cyan_red))
        green = green.point(lambda i: i + (i * self.magenta_green))
        blue = blue.point(lambda i: i + (i * self.yellow_blue))
        image = Image.merge("RGBA", (red, green, blue, alpha))
        return image
