from PIL.ImageFilter import BoxBlur as ImageFilterBoxBlur
from airunner.filters.base_filter import BaseFilter


class BoxBlur(BaseFilter):
    def apply_filter(self, image, do_reset=False):
        print("APPLY FILTER")
        return image.filter(ImageFilterBoxBlur(radius=self.radius))
