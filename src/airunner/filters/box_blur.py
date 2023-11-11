from PIL.ImageFilter import BoxBlur

from airunner.filters.base_filter import BaseFilter


class BoxBlur(BaseFilter):
    def apply_filter(self, image, do_reset):
        return image.filter(BoxBlur(radius=self.radius))
