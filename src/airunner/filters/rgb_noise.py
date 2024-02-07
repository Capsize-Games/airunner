from PIL import Image

from airunner.filters.base_filter import BaseFilter


class RGBNoiseFilter(BaseFilter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.red_grain = None
        self.green_grain = None
        self.blue_grain = None

    def apply_filter(self, image, do_reset):
        self.red_grain = Image.new("L", image.size)
        self.green_grain = Image.new("L", image.size)
        self.blue_grain = Image.new("L", image.size)
        self.red_grain = self.red_grain.point(lambda i: i + (i * self.red))
        self.green_grain = self.green_grain.point(lambda i: i + (i * self.green))
        self.blue_grain = self.blue_grain.point(lambda i: i + (i * self.blue))

        red, green, blue, alpha = image.split()
        red = Image.blend(red, self.red_grain, self.red)
        green = Image.blend(green, self.green_grain, self.green)
        blue = Image.blend(blue, self.blue_grain, self.blue)
        image = Image.merge("RGBA", (red, green, blue, alpha))
        return image