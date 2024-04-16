from PIL import Image, ImageDraw
from airunner.filters.base_filter import BaseFilter


class HalftoneFilter(BaseFilter):
    def apply_filter(self, image, _do_reset):
        img = image.convert(self.color_mode)
        sample = self.sample + 2

        width, height = img.size
        img_small = img.resize((width // sample, height // sample))
        sm_width, sm_height = img_small.size

        img_large = Image.new(self.color_mode, (width, height))
        draw = ImageDraw.Draw(img_large)

        for x in range(0, sm_width):
            for y in range(0, sm_height):
                color = img_small.getpixel((x, y))
                if self.color_mode == "L":
                    radius = (color / 255) * (sample // 2) * self.scale
                else:
                    radius = (color[0] / 255) * (sample // 2) * self.scale
                draw.ellipse([
                    (x * sample - radius, y * sample - radius),
                    (x * sample + radius, y * sample + radius)
                ], fill=color)

        img_large = img_large.convert('RGBA')
        return img_large
