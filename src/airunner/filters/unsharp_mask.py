from PIL.ImageFilter import UnsharpMask

from airunner.filters.base_filter import BaseFilter


class UnsharpMask(BaseFilter):
    def __init__(self, radius, percent, threshold):
        self.unsharp_mask = UnsharpMask(radius=radius, percent=percent, threshold=threshold)

    def apply_filter(self, image, do_reset):
        return image.filter(self.unsharp_mask)
