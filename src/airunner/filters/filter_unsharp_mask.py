from PIL.ImageFilter import UnsharpMask
from airunner.filters.filter_base import FilterBase


class FilterUnsharpMask(FilterBase):
    ui_name = "unsharp_mask_window"
    window_title = "Unsharp Mask"
    unsharp_radius = 50.0
    unsharp_percent = 50.0
    unsharp_threshold = 50.0

    @property
    def filter(self):
        return UnsharpMask(
            radius=self.unsharp_radius,
            percent=int(self.unsharp_percent),
            threshold=int(self.unsharp_threshold)
        )

    def show(self):
        super().show()

        def update_filter():
            self.parent.current_filter = self.filter
            self.canvas.update()

        def handle_unsharp_radius_slider_change(val):
            self.unsharp_radius = val
            self.filter_window.radius_spinbox.setValue(val)
            self.filter_window.radius_spinbox.update()
            self.filter_window.radius_slider.update()
            update_filter()

        def handle_unsharp_radius_spinbox_change(val):
            self.unsharp_radius = val
            self.filter_window.radius_slider.setValue(int(val))
            self.filter_window.radius_spinbox.update()
            self.filter_window.radius_slider.update()
            update_filter()

        def handle_unsharp_percent_slider_change(val):
            self.unsharp_percent = val
            self.filter_window.percent_spinbox.setValue(val)
            self.filter_window.percent_spinbox.update()
            self.filter_window.percent_slider.update()
            update_filter()

        def handle_unsharp_percent_spinbox_change(val):
            self.unsharp_percent = val
            self.filter_window.percent_slider.setValue(int(val))
            self.filter_window.percent_spinbox.update()
            self.filter_window.percent_slider.update()
            update_filter()

        def handle_unsharp_threshold_slider_change(val):
            self.unsharp_threshold = val
            self.filter_window.threshold_spinbox.setValue(val)
            self.filter_window.threshold_spinbox.update()
            self.filter_window.threshold_slider.update()
            update_filter()

        def handle_unsharp_threshold_spinbox_change(val):
            self.unsharp_threshold = val
            self.filter_window.threshold_slider.setValue(int(val))
            self.filter_window.threshold_spinbox.update()
            self.filter_window.threshold_slider.update()
            update_filter()

        # set the gaussian_blur_window settings values to the current settings
        self.filter_window.radius_slider.setValue(int(self.unsharp_radius))
        self.filter_window.radius_slider.valueChanged.connect(lambda val: handle_unsharp_radius_slider_change(val))
        self.filter_window.radius_spinbox.setValue(self.unsharp_radius)
        self.filter_window.radius_spinbox.valueChanged.connect(lambda val: handle_unsharp_radius_spinbox_change(val))

        self.filter_window.percent_slider.setValue(int(self.unsharp_percent))
        self.filter_window.percent_slider.valueChanged.connect(lambda val: handle_unsharp_percent_slider_change(val))
        self.filter_window.percent_spinbox.setValue(self.unsharp_percent)
        self.filter_window.percent_spinbox.valueChanged.connect(lambda val: handle_unsharp_percent_spinbox_change(val))

        self.filter_window.threshold_slider.setValue(int(self.unsharp_threshold))
        self.filter_window.threshold_slider.valueChanged.connect(lambda val: handle_unsharp_threshold_slider_change(val))
        self.filter_window.threshold_spinbox.setValue(self.unsharp_threshold)
        self.filter_window.threshold_spinbox.valueChanged.connect(lambda val: handle_unsharp_threshold_spinbox_change(val))
        self.filter_window = self.filter_window
        # on ok button click, apply the filter
        self.filter_window.buttonBox.rejected.connect(self.cancel_filter)
        self.filter_window.buttonBox.accepted.connect(self.apply_filter)

        self.parent.current_filter = self.filter

        self.filter_window.exec()
