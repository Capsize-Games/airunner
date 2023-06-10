from airunner.filters.filter_base import FilterBase
from aihandler.qtvar import FloatVar
from airunner.filters.rgb_noise_filter import RGBNoiseFilter
from PIL import Image
import random

class FilterRGBNoise(FilterBase):
    ui_name = "noise_filter"
    window_title = "RGB Noise Filter"
    red_noise = 0.0
    green_noise = 0.0
    blue_noise = 0.0
    red_grain = None
    green_grain = None
    blue_grain = None

    @property
    def filter(self):
        return RGBNoiseFilter(
            self.red_noise / 1000.0,
            self.green_noise / 1000.0,
            self.blue_noise / 1000.0,
            self.red_grain,
            self.green_grain,
            self.blue_grain
        )

    def show(self):
        super().show()

        working_images = self.parent.canvas.current_active_image
        if working_images is not None:
            image = working_images.image.copy()

            self.red_grain = Image.new("L", image.size)
            self.green_grain = Image.new("L", image.size)
            self.blue_grain = Image.new("L", image.size)

            self.red_grain.putdata([random.randint(0, 255) for i in range(image.size[0] * image.size[1])])
            self.green_grain.putdata([random.randint(0, 255) for i in range(image.size[0] * image.size[1])])
            self.blue_grain.putdata([random.randint(0, 255) for i in range(image.size[0] * image.size[1])])

            self.filter_window.red_slider.setValue(0)
            self.filter_window.green_slider.setValue(0)
            self.filter_window.blue_slider.setValue(0)

            self.filter_window.red_spinbox.setValue(0)
            self.filter_window.green_spinbox.setValue(0)
            self.filter_window.blue_spinbox.setValue(0)

            self.filter_window.red_slider.valueChanged.connect(self.noise_red_slider_change)
            self.filter_window.green_slider.valueChanged.connect(self.noise_green_slider_change)
            self.filter_window.blue_slider.valueChanged.connect(self.noise_blue_slider_change)

            self.filter_window.red_spinbox.valueChanged.connect(self.noise_red_spinbox_change)
            self.filter_window.green_spinbox.valueChanged.connect(self.noise_green_spinbox_change)
            self.filter_window.blue_spinbox.valueChanged.connect(self.noise_blue_spinbox_change)
            self.filter_window.buttonBox.rejected.connect(self.cancel_filter)
            self.filter_window.buttonBox.accepted.connect(self.apply_filter)
        self.preview_filter()
        self.filter_window.exec()

    def noise_red_slider_change(self, val):
        self.red_noise = val
        self.filter_window.red_spinbox.setValue(val / 1000.0)
        self.filter_window.red_spinbox.update()
        self.preview_filter()

    def noise_green_slider_change(self, val):
        self.green_noise = val
        self.filter_window.green_spinbox.setValue(val / 1000.0)
        self.filter_window.green_spinbox.update()
        self.preview_filter()

    def noise_blue_slider_change(self, val):
        self.blue_noise = val
        self.filter_window.blue_spinbox.setValue(val / 1000.0)
        self.filter_window.blue_spinbox.update()
        self.preview_filter()

    def noise_red_spinbox_change(self, val):
        self.red_noise = val * 1000
        self.filter_window.red_slider.setValue(int(val * 1000))
        self.filter_window.red_slider.update()
        self.preview_filter()

    def noise_green_spinbox_change(self, val):
        self.green_noise = val * 1000
        self.filter_window.green_slider.setValue(int(val * 1000))
        self.filter_window.green_slider.update()
        self.preview_filter()

    def noise_blue_spinbox_change(self, val):
        self.blue_noise = val * 1000
        self.filter_window.blue_slider.setValue(int(val * 1000))
        self.filter_window.blue_slider.update()
        self.preview_filter()