from airunner.filters.filter_base import FilterBase
from airunner.filters.pixel_filter import PixelFilter


class FilterPixelArt(FilterBase):
    ui_name = "pixel_art"
    window_title = "Pixel Art"
    number_of_colors = 24
    smoothing = 1
    base_size = 256

    @property
    def filter(self):
        return PixelFilter(
            number_of_colors=self.number_of_colors,
            smoothing=self.smoothing,
            base_size=self.base_size
        )

    def show(self):
        super().show()
        self.parent.current_filter = self.filter

        # set the gaussian_blur_window settings values to the current settings
        self.filter_window.number_of_colors_slider.setValue(self.number_of_colors)
        self.filter_window.number_of_colors_spinbox.setValue(self.number_of_colors)
        self.filter_window.number_of_colors_slider.valueChanged.connect(
            lambda val: self.handle_number_of_colors_change_slider(val))
        self.filter_window.number_of_colors_spinbox.valueChanged.connect(
            lambda val: self.handle_number_of_colors_change_spinbox(val))

        # ensure base_size is multiple of 16
        self.filter_window.base_size_slider.setValue(self.base_size)
        self.filter_window.base_size_spinbox.setValue(self.base_size)
        self.filter_window.base_size_slider.valueChanged.connect(
            lambda val: self.handle_base_size_change_slider(val))
        self.filter_window.base_size_spinbox.valueChanged.connect(
            lambda val: self.handle_base_size_change_spinbox(val))

        # on ok button click, apply the filter
        self.filter_window.buttonBox.rejected.connect(self.cancel_filter)
        self.filter_window.buttonBox.accepted.connect(self.apply_filter)

        # apply the filter
        self.parent.current_filter = self.filter
        self.canvas.apply_filter()
        self.update_canvas()

        self.filter_window.exec()

    def handle_number_of_colors_change_slider(self, val):
        self.handle_number_of_colors_change(val)
        self.filter_window.number_of_colors_spinbox.setValue(val)

    def handle_number_of_colors_change_spinbox(self, val):
        self.handle_number_of_colors_change(val)
        self.filter_window.number_of_colors_slider.setValue(val)

    def handle_number_of_colors_change(self, val):
        self.number_of_colors = val
        self.parent.current_filter = self.filter
        self.canvas.update()

    def handle_base_size_change_slider(self, val):
        val = val - (val % 16)
        self.handle_base_size_change(val)
        self.filter_window.base_size_spinbox.setValue(val)

    def handle_base_size_change_spinbox(self, val):
        val = val - (val % 16)
        self.handle_base_size_change(val)
        self.filter_window.base_size_slider.setValue(val)

    def handle_base_size_change(self, val):
        self.base_size = val
        self.parent.current_filter = self.filter
        self.canvas.update()
