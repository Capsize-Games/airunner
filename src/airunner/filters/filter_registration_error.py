from airunner.filters.filter_base import FilterBase
from airunner.filters.registration_error_filter import RegistrationErrorFilter


class FilterRegistrationError(FilterBase):
    ui_name = "registration_error"
    window_title = "Registration Error"
    red_offset_x_amount = 3
    red_offset_y_amount = 3
    green_offset_x_amount = 6
    green_offset_y_amount = 6
    blue_offset_x_amount = 9
    blue_offset_y_amount = 9

    @property
    def filter(self):
        if self._filter is None:
            self._filter = RegistrationErrorFilter(
                red_offset_x_amount=self.red_offset_x_amount,
                red_offset_y_amount=self.red_offset_y_amount,
                green_offset_x_amount=self.green_offset_x_amount,
                green_offset_y_amount=self.green_offset_y_amount,
                blue_offset_x_amount=self.blue_offset_x_amount,
                blue_offset_y_amount=self.blue_offset_y_amount
            )
        else:
            self._filter.red_offset_x_amount = self.red_offset_x_amount
            self._filter.red_offset_y_amount = self.red_offset_y_amount
            self._filter.green_offset_x_amount = self.green_offset_x_amount
            self._filter.green_offset_y_amount = self.green_offset_y_amount
            self._filter.blue_offset_x_amount = self.blue_offset_x_amount
            self._filter.blue_offset_y_amount = self.blue_offset_y_amount
        return self._filter

    def show(self):
        super().show()

        self.filter_window.red_offset_x_amount_slider.setValue(self.red_offset_x_amount)
        self.filter_window.red_offset_x_amount_spinbox.setValue(self.red_offset_x_amount)
        self.filter_window.red_offset_x_amount_slider.valueChanged.connect(
            lambda val: self.handle_offset_x_amount_change_slider(val, "red"))
        self.filter_window.red_offset_x_amount_spinbox.valueChanged.connect(
            lambda val: self.handle_offset_x_amount_change_spinbox(val, "red"))

        self.filter_window.red_offset_y_amount_slider.setValue(self.red_offset_x_amount)
        self.filter_window.red_offset_y_amount_spinbox.setValue(self.red_offset_x_amount)
        self.filter_window.red_offset_y_amount_slider.valueChanged.connect(
            lambda val: self.handle_offset_y_amount_change_slider(val, "red"))
        self.filter_window.red_offset_y_amount_spinbox.valueChanged.connect(
            lambda val: self.handle_offset_y_amount_change_spinbox(val, "red"))

        self.filter_window.green_offset_x_amount_slider.setValue(self.green_offset_x_amount)
        self.filter_window.green_offset_x_amount_spinbox.setValue(self.green_offset_x_amount)
        self.filter_window.green_offset_x_amount_slider.valueChanged.connect(
            lambda val: self.handle_offset_x_amount_change_slider(val, "green"))
        self.filter_window.green_offset_x_amount_spinbox.valueChanged.connect(
            lambda val: self.handle_offset_x_amount_change_spinbox(val, "green"))

        self.filter_window.green_offset_y_amount_slider.setValue(self.green_offset_x_amount)
        self.filter_window.green_offset_y_amount_spinbox.setValue(self.green_offset_x_amount)
        self.filter_window.green_offset_y_amount_slider.valueChanged.connect(
            lambda val: self.handle_offset_y_amount_change_slider(val, "green"))
        self.filter_window.green_offset_y_amount_spinbox.valueChanged.connect(
            lambda val: self.handle_offset_y_amount_change_spinbox(val, "green"))

        self.filter_window.blue_offset_x_amount_slider.setValue(self.blue_offset_x_amount)
        self.filter_window.blue_offset_x_amount_spinbox.setValue(self.blue_offset_x_amount)
        self.filter_window.blue_offset_x_amount_slider.valueChanged.connect(
            lambda val: self.handle_offset_x_amount_change_slider(val, "blue"))
        self.filter_window.blue_offset_x_amount_spinbox.valueChanged.connect(
            lambda val: self.handle_offset_x_amount_change_spinbox(val, "blue"))

        self.filter_window.blue_offset_y_amount_slider.setValue(self.blue_offset_x_amount)
        self.filter_window.blue_offset_y_amount_spinbox.setValue(self.blue_offset_x_amount)
        self.filter_window.blue_offset_y_amount_slider.valueChanged.connect(
            lambda val: self.handle_offset_y_amount_change_slider(val, "blue"))
        self.filter_window.blue_offset_y_amount_spinbox.valueChanged.connect(
            lambda val: self.handle_offset_y_amount_change_spinbox(val, "blue"))

        # on ok button click, apply the filter
        self.filter_window.buttonBox.rejected.connect(self.cancel_filter)
        self.filter_window.buttonBox.accepted.connect(self.apply_filter)

        # apply the filter
        self.preview_filter()
        self.filter_window.exec()

    def handle_offset_x_amount_change_slider(self, val, color):
        self.handle_offset_x_change(val, color)

        if color == "red":
            self.filter_window.red_offset_x_amount_spinbox.setValue(val)
        elif color == "green":
            self.filter_window.green_offset_x_amount_spinbox.setValue(val)
        elif color == "blue":
            self.filter_window.blue_offset_x_amount_spinbox.setValue(val)

    def handle_offset_x_amount_change_spinbox(self, val, color):
        self.handle_offset_x_change(val, color)
        if color == "red":
            self.filter_window.red_offset_x_amount_slider.setValue(val)
        elif color == "green":
            self.filter_window.green_offset_x_amount_slider.setValue(val)
        elif color == "blue":
            self.filter_window.blue_offset_x_amount_slider.setValue(val)

    def handle_offset_x_change(self, val, color):
        if color == "red":
            self.red_offset_x_amount = val
        elif color == "green":
            self.green_offset_x_amount = val
        elif color == "blue":
            self.blue_offset_x_amount = val
        self.preview_filter()

    def handle_offset_y_amount_change_slider(self, val, color):
        self.handle_offset_y_change(val, color)
        if color == "red":
            self.filter_window.red_offset_y_amount_spinbox.setValue(val)
        elif color == "green":
            self.filter_window.green_offset_y_amount_spinbox.setValue(val)
        elif color == "blue":
            self.filter_window.blue_offset_y_amount_spinbox.setValue(val)

    def handle_offset_y_amount_change_spinbox(self, val, color):
        self.handle_offset_y_change(val, color)
        if color == "red":
            self.filter_window.red_offset_y_amount_slider.setValue(val)
        elif color == "green":
            self.filter_window.green_offset_y_amount_slider.setValue(val)
        elif color == "blue":
            self.filter_window.blue_offset_y_amount_slider.setValue(val)

    def handle_offset_y_change(self, val, color):
        if color == "red":
            self.red_offset_y_amount = val
        elif color == "green":
            self.green_offset_y_amount = val
        elif color == "blue":
            self.blue_offset_y_amount = val
        self.preview_filter()
