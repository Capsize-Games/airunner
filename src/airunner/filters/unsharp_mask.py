from PIL.ImageFilter import UnsharpMask as PILUnsharpMask
from airunner.filters.base_filter import BaseFilter


class UnsharpMask(BaseFilter):
    def apply_filter(self, image, do_reset):
        return image.filter(PILUnsharpMask(radius=self.radius * 100, percent=int(self.percent * 200), threshold=int(self.threshold * 10)))
