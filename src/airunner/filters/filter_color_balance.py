from airunner.filters.color_balance_filter import ColorBalanceFilter
from airunner.filters.filter_base import FilterBase


class FilterColorBalance(FilterBase):
    ui_name = "color_balance"
    window_title = "Color Balance"

    def __init__(self, parent):
        super().__init__(parent)
        self.cyan_red = parent.settings_manager.settings.cyan_red
        self.magenta_green = parent.settings_manager.settings.magenta_green
        self.yellow_blue = parent.settings_manager.settings.yellow_blue

    @property
    def filter(self):
        return ColorBalanceFilter(
            cyan_red=self.cyan_red.get() / 1000,
            magenta_green=self.magenta_green.get() / 1000,
            yellow_blue=self.yellow_blue.get() / 1000
        )

    def show(self):
        super().show()

        self.cyan_red.set(0)
        self.magenta_green.set(0)
        self.yellow_blue.set(0)

        def update_filter():
            self.parent.current_filter = self.filter
            self.canvas.update()

        def color_balance_cyan_slider_change(val):
            self.filter_window.cyan_spinbox.setValue(val / 1000.0)
            self.filter_window.cyan_spinbox.update()
            update_filter()

        def color_balance_magenta_slider_change(val):
            self.filter_window.magenta_spinbox.setValue(val / 1000.0)
            self.filter_window.magenta_spinbox.update()
            update_filter()

        def color_balance_yellow_slider_change(val):
            self.filter_window.yellow_spinbox.setValue(val / 1000.0)
            self.filter_window.yellow_spinbox.update()
            update_filter()

        def color_balance_cyan_spinbox_change(val):
            self.filter_window.cyan_slider.setValue(int(val * 1000.0))
            self.filter_window.cyan_slider.update()
            update_filter()

        def color_balance_magenta_spinbox_change(val):
            self.filter_window.magenta_slider.setValue(int(val * 1000.0))
            self.filter_window.magenta_slider.update()
            update_filter()

        def color_balance_yellow_spinbox_change(val):
            self.filter_window.yellow_slider.setValue(int(val * 1000.0))
            self.filter_window.yellow_slider.update()
            update_filter()

        self.filter_window.cyan_slider.setValue(self.cyan_red.get())
        self.filter_window.cyan_slider.valueChanged.connect(lambda val: color_balance_cyan_slider_change(val))
        self.filter_window.cyan_spinbox.setValue(self.cyan_red.get() / 1000.0)
        self.filter_window.cyan_spinbox.valueChanged.connect(lambda val: color_balance_cyan_spinbox_change(val))

        self.filter_window.magenta_slider.setValue(self.magenta_green.get())
        self.filter_window.magenta_slider.valueChanged.connect(lambda val: color_balance_magenta_slider_change(val))
        self.filter_window.magenta_spinbox.setValue(self.magenta_green.get() / 1000.0)
        self.filter_window.magenta_spinbox.valueChanged.connect(lambda val: color_balance_magenta_spinbox_change(val))

        self.filter_window.yellow_slider.setValue(self.yellow_blue.get())
        self.filter_window.yellow_slider.valueChanged.connect(lambda val: color_balance_yellow_slider_change(val))
        self.filter_window.yellow_spinbox.setValue(self.yellow_blue.get() / 1000.0)
        self.filter_window.yellow_spinbox.valueChanged.connect(lambda val: color_balance_yellow_spinbox_change(val))

        # on ok button click, apply the filter
        self.filter_window.buttonBox.rejected.connect(self.cancel_filter)
        self.filter_window.buttonBox.accepted.connect(self.apply_filter)

        self.filter_window.exec()
