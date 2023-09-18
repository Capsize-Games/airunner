from PIL.ImageFilter import UnsharpMask

from airunner.filters.base_filter import BaseFilter


class UnsharpMask(BaseFilter):
    def apply_filter(self, image, do_reset):
        return image.filter(UnsharpMask(radius=self.radius))
