from PIL.ImageFilter import UnsharpMask

from airunner.filters.base_filter import BaseFilter


class UnsharpMask(BaseFilter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.unsharp_mask = UnsharpMask(**kwargs)

    def apply_filter(self, image, do_reset):
        return image.filter(self.unsharp_mask)
