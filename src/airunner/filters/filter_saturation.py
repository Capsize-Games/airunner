from airunner.filters.filter_base import FilterBase
from airunner.filters.saturation_filter import SaturationFilter


class FilterSaturation(FilterBase):
    ui_name = "saturation_window"
    window_title = "Saturation"
    factor = 0

    @property
    def filter(self):
        return SaturationFilter(factor=self.factor / 1000)

    def show(self):
        super().show()
        # set the gaussian_blur_window settings values to the current settings
        self.filter_window.blur_slider.setValue(int(self.factor))
        self.filter_window.blur_slider.valueChanged.connect(
            lambda val: self.handle_blur_radius_slider_change(val))
        self.filter_window.blur_spinbox.setValue(self.factor / 1000.0)
        self.filter_window.blur_spinbox.valueChanged.connect(
            lambda val: self.handle_blur_radius_spinbox_change(val))

        # on ok button click, apply the filter
        self.filter_window.buttonBox.rejected.connect(self.cancel_filter)
        self.filter_window.buttonBox.accepted.connect(self.apply_filter)

        self.filter_window.exec()

    def handle_blur_radius_slider_change(self, val):
        self.factor = float(val)
        self.filter_window.blur_spinbox.setValue(val / 1000.0)
        self.parent.current_filter = self.filter
        self.canvas.update()

    def handle_blur_radius_spinbox_change(self, val):
        self.factor = val / 100.0
        self.filter_window.blur_slider.setValue(int(val * 1000.0))
        self.parent.current_filter = self.filter
        self.update_canvas()
