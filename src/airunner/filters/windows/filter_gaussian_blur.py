from PIL.ImageFilter import GaussianBlur

from airunner.filters.windows.blur_filter import BlurFilter


class FilterGaussianBlur(BlurFilter):
    ui_name = "gaussian_blur_window"
    window_title = "Gaussian Blur"
    default_value = 0

    @property
    def filter(self):
        return GaussianBlur(radius=self.blur_radius.get()*20)
