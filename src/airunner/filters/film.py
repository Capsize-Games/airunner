from airunner.filters.base_filter import BaseFilter
from airunner.filters.box_blur import BoxBlur
from airunner.filters.rgb_noise import RGBNoiseFilter


class FilmFilter(BaseFilter):
    current_number_of_colors = 0

    def apply_filter(self, image, do_reset):
        image = BoxBlur(
            radius=self.radius
        ).filter(image)
        image = RGBNoiseFilter(
            red=self.red,
            green=self.green,
            blue=self.blue
        ).filter(image)
        return image
