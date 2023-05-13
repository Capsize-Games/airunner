from PIL.ImageFilter import GaussianBlur
from airunner.filters.blur_filter import BlurFilter


class FilterGaussianBlur(BlurFilter):
    ui_name = "gaussian_blur_window"
    window_title = "Gaussian Blur"
    default_value = 1.0

    @property
    def filter(self):
        return GaussianBlur(radius=self.blur_radius.get())
