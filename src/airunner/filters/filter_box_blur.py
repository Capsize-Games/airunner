from PIL.ImageFilter import BoxBlur
from airunner.filters.blur_filter import BlurFilter


class FilterBoxBlur(BlurFilter):
    ui_name = "box_blur_window"
    window_title = "Box Blur"
    default_value = 0

    @property
    def filter(self):
        return BoxBlur(radius=self.blur_radius.get()*20)
