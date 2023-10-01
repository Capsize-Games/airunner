from functools import partial

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QLabel, QSlider, QDoubleSpinBox

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.slider.templates.slider_ui import Ui_slider_widget


class SliderWidget(BaseWidget):
    widget_class_ = Ui_slider_widget
    display_as_float = False
    divide_by = 1.0

    @property
    def slider_single_step(self):
        return self.ui.slider.singleStep()

    @slider_single_step.setter
    def slider_single_step(self, val):
        self.ui.slider.setSingleStep(val)

    @property
    def slider_page_step(self):
        return self.ui.slider.pageStep()

    @slider_page_step.setter
    def slider_page_step(self, val):
        self.ui.slider.setPageStep(val)

    @property
    def spinbox_single_step(self):
        return self.ui.spinbox.singleStep

    @spinbox_single_step.setter
    def spinbox_single_step(self, val):
        self.ui.spinbox.setSingleStep(val)

    @property
    def spinbox_page_step(self):
        return self.ui.spinbox.pageStep

    @spinbox_page_step.setter
    def spinbox_page_step(self, val):
        self.ui.spinbox.pageStep = val

    @property
    def slider_tick_interval(self):
        return self.ui.slider.tickInterval()

    @slider_tick_interval.setter
    def slider_tick_interval(self, val):
        self.ui.slider.tickInterval = val

    @property
    def slider_minimum(self):
        return self.ui.slider.minimum

    @slider_minimum.setter
    def slider_minimum(self, val):
        self.ui.slider.minimum = val

    @property
    def slider_maximum(self):
        return self.ui.slider.maximum()

    @slider_maximum.setter
    def slider_maximum(self, val):
        self.ui.slider.setMaximum(val)

    @property
    def spinbox_maximum(self):
        return self.ui.spinbox.maximum()

    @spinbox_maximum.setter
    def spinbox_maximum(self, val):
        self.ui.spinbox.setMaximum(val)

    @property
    def spinbox_minimum(self):
        return self.ui.spinbox.minimum()

    @spinbox_minimum.setter
    def spinbox_minimum(self, val):
        self.ui.spinbox.setMinimum(val)

    def initialize(self):
        slider_minimum = self.property("slider_minimum") or 0
        slider_maximum = self.property("slider_maximum") or 100
        slider_tick_interval = self.property("slider_tick_interval") or 8
        slider_callback = self.property("slider_callback") or ""
        slider_single_step = self.property("slider_single_step") or 1
        slider_page_step = self.property("slider_page_step") or 1
        spinbox_minimum = self.property("spinbox_minimum") or 0
        spinbox_maximum = self.property("spinbox_maximum") or 100.0
        spinbox_single_step = self.property("spinbox_single_step") or 0.01
        spinbox_page_step = self.property("spinbox_page_step") or 0.01
        label_text = self.property("label_text") or ""
        current_value = self.property("current_value") or 0
        slider_name = self.property("slider_name") or None
        spinbox_name = self.property("spinbox_name") or None
        settings_property = self.property("settings_property") or None
        self.display_as_float = self.property("display_as_float") or True
        self.divide_by = self.property("divide_by") or 1.0

        if slider_callback != "":
            slider_callback = partial(getattr(self.app, slider_callback), settings_property)

        # set slider and spinbox names
        if slider_name:
            self.ui.slider.setObjectName(slider_name)

        if spinbox_name:
            self.ui.spinbox.setObjectName(spinbox_name)

        self.ui.slider_callback = slider_callback
        self.ui.slider_maximum = slider_maximum
        self.ui.slider_minimum = slider_minimum
        self.ui.slider_tick_interval = slider_tick_interval
        self.ui.slider_single_step = slider_single_step
        self.ui.slider_page_step = slider_page_step
        self.ui.spinbox_single_step = spinbox_single_step
        self.ui.spinbox_page_step = spinbox_page_step
        self.ui.spinbox_minimum = spinbox_minimum
        self.ui.spinbox_maximum = spinbox_maximum
        self.ui.label_text = label_text

        self.label = QLabel(f"{label_text}")
        self.set_stylesheet()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.ui.slider.valueChanged.connect(self.handle_slider_change)
        #self.ui.slider.valueChanged.connect(lambda value: self.ui.spinbox.setValue(value / self.ui.slider_maximum))
        # add the label to the ui
        self.layout().addWidget(self.label, 0, 0, 1, 2)
        # self.ui.spinbox.lineEdit().hide()
        self.ui.spinbox.setFixedWidth(75)
        self.ui.spinbox.valueChanged.connect(self.handle_spinbox_change)
        self.ui.slider.setValue(int(current_value))

        if not self.display_as_float:
            self.ui.spinbox.setDecimals(0)

    def set_stylesheet(self):
        self.ui.slider.setStyleSheet(self.app.css("slider"))
        self.label.setStyleSheet(self.app.css("slider_label"))
        self.ui.spinbox.setStyleSheet(self.app.css("slider_spinbox"))

    def handle_spinbox_change(self, val):
        normalized = val / self.ui.spinbox_maximum
        slider_val = normalized * self.ui.slider_maximum
        self.ui.slider.setValue(round(slider_val))
        # self.update_label()

    def handle_slider_change(self, val):
        position = val#self.ui.slider.sliderPosition()
        single_step = self.ui.slider.singleStep()
        adjusted_value = round(position / single_step) * single_step
        if adjusted_value < self.ui.slider_minimum:
            adjusted_value = self.ui.slider_minimum
        self.ui.slider.setValue(int(adjusted_value))

        normalized = adjusted_value / self.ui.slider_maximum
        spinbox_val = normalized * self.ui.spinbox_maximum
        spinbox_val = round(spinbox_val, 2)
        self.ui.spinbox.setValue(spinbox_val)

        # self.update_label()
        if self.ui.slider_callback:
            self.ui.slider_callback(adjusted_value)

    def update_value(self, val):
        self.ui.slider.setValue(int(val))

        if self.display_as_float:
            val = self.ui.spinbox.value()

        # self.update_label()

    # def update_label(self):
    #     if self.display_as_float:
    #         val = f"{self.ui.spinbox.value():.2f}"
    #     else:
    #         val = f"{int(self.ui.spinbox.value())}"
    #     self.label.setText(f"{self.label_text} {val}")

    def set_tick_value(self, val):
        """
        This will set all intervals in spinbox and slider to the same amount.
        :param val:
        :return:
        """
        self.ui.slider_minimum = val
        self.ui.slider_tick_interval = val
        self.ui.slider_single_step = val
        self.ui.slider_page_step = val
        self.ui.spinbox_single_step = val
        self.ui.spinbox_page_step = val
        self.ui.spinbox_minimum = val

    def setValue(self, val):
        self.ui.slider.setValue(val)
