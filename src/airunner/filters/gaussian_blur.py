from PIL.ImageFilter import GaussianBlur as PILGaussianBlur
from airunner.filters.base_filter import BaseFilter

class GaussianBlur(BaseFilter):
    def apply_filter(self, image, do_reset):
        return image.filter(PILGaussianBlur(radius=self.radius))