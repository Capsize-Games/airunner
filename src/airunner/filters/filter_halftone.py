from airunner.filters.filter_base import FilterBase
from airunner.filters.halftone_filter import HalftoneFilter
from airunner.filters.pixel_filter import PixelFilter


class FilterHalftone(FilterBase):
    ui_name = "halftone_filter"
    window_title = "Halftone Filter"
    color_mode = "L"
    sample = 1
    scale = 1

    @property
    def filter(self):
        if self._filter is None:
            self._filter = HalftoneFilter(
                sample=self.sample,
                scale=self.scale,
                color_mode=self.color_mode
            )
        else:
            self._filter.sample = self.sample
            self._filter.scale = self.scale
            self._filter.color_mode = self.color_mode
        return self._filter

    def show(self):
        super().show()

        self.filter_window.sample_slider.setValue(self.sample)
        self.filter_window.sample_spinbox.setValue(self.sample)
        self.filter_window.sample_slider.valueChanged.connect(
            lambda val: self.handle_sample_change_slider(val))
        self.filter_window.sample_spinbox.valueChanged.connect(
            lambda val: self.handle_sample_spinbox_change_spinbox(val))

        self.filter_window.scale_slider.setValue(self.scale)
        self.filter_window.scale_spinbox.setValue(self.scale)
        self.filter_window.scale_slider.valueChanged.connect(
            lambda val: self.handle_scale_change_slider(val))
        self.filter_window.scale_spinbox.valueChanged.connect(
            lambda val: self.handle_scale_change_spinbox(val))

        self.filter_window.color_mode.currentIndexChanged.connect(
            lambda val: self.handle_color_mode_change(val))

        # on ok button click, apply the filter
        self.filter_window.buttonBox.rejected.connect(self.cancel_filter)
        self.filter_window.buttonBox.accepted.connect(self.apply_filter)

        # apply the filter
        self.preview_filter()
        self.filter_window.exec()

    def handle_sample_change_slider(self, val):
        self.handle_sample_change(val)
        self.filter_window.sample_spinbox.setValue(val)

    def handle_sample_spinbox_change_spinbox(self, val):
        self.handle_sample_change(val)
        self.filter_window.sample_slider.setValue(val)

    def handle_sample_change(self, val):
        self.sample = val
        self.preview_filter()

    def handle_scale_change_slider(self, val):
        self.handle_scale_change(val)
        self.filter_window.scale_spinbox.setValue(val)

    def handle_scale_change_spinbox(self, val):
        self.handle_scale_change(val)
        self.filter_window.scale_slider.setValue(val)

    def handle_scale_change(self, val):
        self.scale = val
        self.preview_filter()

    def handle_color_mode_change(self, val):
        mode = self.filter_window.color_mode.currentText()
        if mode == "Black and White":
            mode = "L"
        self.color_mode = mode
        self.preview_filter()
