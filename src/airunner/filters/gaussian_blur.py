from PIL.ImageFilter import GaussianBlur

from airunner.filters.base_filter import BaseFilter


class GaussianBlur(BaseFilter):
    def apply_filter(self, image, do_reset):
        return image.filter(GaussianBlur(radius=self.radius))
