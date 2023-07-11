from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QLabel, QSlider, QDoubleSpinBox


class SliderWidget(QWidget):
    @property
    def slider_single_step(self):
        return self.slider.singleStep()

    @slider_single_step.setter
    def slider_single_step(self, val):
        self.slider.setSingleStep(val)

    @property
    def slider_page_step(self):
        return self.slider.pageStep()

    @slider_page_step.setter
    def slider_page_step(self, val):
        self.slider.setPageStep(val)

    @property
    def spinbox_single_step(self):
        return self.spinbox.singleStep

    @spinbox_single_step.setter
    def spinbox_single_step(self, val):
        self.spinbox.setSingleStep(val)

    @property
    def spinbox_page_step(self):
        return self.spinbox.pageStep

    @spinbox_page_step.setter
    def spinbox_page_step(self, val):
        self.spinbox.pageStep = val

    @property
    def slider_tick_interval(self):
        return self.slider.tickInterval()

    @slider_tick_interval.setter
    def slider_tick_interval(self, val):
        self.slider.tickInterval = val

    @property
    def slider_minimum(self):
        return self.slider.minimum

    @slider_minimum.setter
    def slider_minimum(self, val):
        self.slider.minimum = val

    @property
    def slider_maximum(self):
        return self.slider.maximum()

    @slider_maximum.setter
    def slider_maximum(self, val):
        self.slider.setMaximum(val)

    @property
    def spinbox_maximum(self):
        return self.spinbox.maximum()

    @spinbox_maximum.setter
    def spinbox_maximum(self, val):
        self.spinbox.setMaximum(val)

    @property
    def spinbox_minimum(self):
        return self.spinbox.minimum()

    @spinbox_minimum.setter
    def spinbox_minimum(self, val):
        self.spinbox.setMinimum(val)

    def __init__(self, *args, **kwargs):
        self.app = kwargs.pop("app", None)
        slider_minimum = kwargs.pop("slider_minimum", 0)
        slider_maximum = kwargs.pop("slider_maximum", 100)
        slider_tick_interval = kwargs.pop("slider_tick_interval", 8)
        slider_callback = kwargs.pop("slider_callback", None)
        slider_single_step = kwargs.pop("slider_single_step", 1)
        slider_page_step = kwargs.pop("slider_page_step", 1)
        spinbox_minimum = kwargs.pop("spinbox_minimum", 0)
        spinbox_maximum = kwargs.pop("spinbox_maximum", 100.0)
        spinbox_single_step = kwargs.pop("spinbox_single_step", 0.01)
        spinbox_page_step = kwargs.pop("spinbox_page_step", 0.01)
        label_text = kwargs.pop("label_text", "")
        current_value = kwargs.pop("current_value", 0)
        parent = kwargs.pop("parent", None)
        slider_name = kwargs.pop("slider_name", None)
        spinbox_name = kwargs.pop("spinbox_name", None)
        self.display_as_float = kwargs.pop("display_as_float", True)
        self.divide_by = kwargs.pop("divide_by", 1.0)

        super().__init__(*args, **kwargs)

        uic.loadUi("pyqt/widgets/slider.ui", self)

        if parent:
            self.setParent(parent)

        # set slider and spinbox names
        if slider_name:
            self.slider.setObjectName(slider_name)

        if spinbox_name:
            self.spinbox.setObjectName(spinbox_name)

        self.slider_callback = slider_callback
        self.slider_maximum = slider_maximum
        self.slider_minimum = slider_minimum
        self.slider_tick_interval = slider_tick_interval
        self.slider_single_step = slider_single_step
        self.slider_page_step = slider_page_step
        self.spinbox_single_step = spinbox_single_step
        self.spinbox_page_step = spinbox_page_step
        self.spinbox_minimum = spinbox_minimum
        self.spinbox_maximum = spinbox_maximum
        self.label_text = label_text

        self.label = QLabel(f"{self.label_text} 0")
        self.set_stylesheet()
        self.layout().removeWidget(self.slider)
        self.layout().removeWidget(self.spinbox)
        self.layout().addWidget(self.slider, 0, 0, 1, 1)
        self.layout().addWidget(self.spinbox, 0, 1, 1, 1)
        self.slider.raise_()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.slider.valueChanged.connect(self.handle_slider_change)
        #self.slider.valueChanged.connect(lambda value: self.spinbox.setValue(value / self.slider_maximum))
        self.layout().addWidget(self.label, 0, 0, 1, 1)
        self.spinbox.lineEdit().hide()
        self.spinbox.setFixedWidth(25)
        self.spinbox.valueChanged.connect(self.handle_spinbox_change)
        self.slider.setValue(int(current_value))

    def set_stylesheet(self):
        self.slider.setStyleSheet(self.app.css("slider"))
        self.label.setStyleSheet(self.app.css("slider_label"))
        self.spinbox.setStyleSheet(self.app.css("slider_spinbox"))

    def handle_spinbox_change(self, val):
        normalized = val / self.spinbox_maximum
        slider_val = normalized * self.slider_maximum
        self.slider.setValue(round(slider_val))
        self.update_label()

    def handle_slider_change(self, val):
        position = val#self.slider.sliderPosition()
        single_step = self.slider.singleStep()
        adjusted_value = round(position / single_step) * single_step
        if adjusted_value < self.slider_minimum:
            adjusted_value = self.slider_minimum
        self.slider.setValue(int(adjusted_value))

        normalized = adjusted_value / self.slider_maximum
        spinbox_val = normalized * self.spinbox_maximum
        spinbox_val = round(spinbox_val, 2)
        self.spinbox.setValue(spinbox_val)

        self.update_label()
        if self.slider_callback:
            self.slider_callback(adjusted_value)

    def update_value(self, val):
        self.slider.setValue(int(val))

        if self.display_as_float:
            val = self.spinbox.value()

        self.update_label()

    def update_label(self):
        if self.display_as_float:
            val = f"{self.spinbox.value():.2f}"
        else:
            val = f"{int(self.spinbox.value())}"
        self.label.setText(f"{self.label_text} {val}")

    def set_tick_value(self, val):
        """
        This will set all intervals in spinbox and slider to the same amount.
        :param val:
        :return:
        """
        self.slider_minimum = val
        self.slider_tick_interval = val
        self.slider_single_step = val
        self.slider_page_step = val
        self.spinbox_single_step = val
        self.spinbox_page_step = val
        self.spinbox_minimum = val