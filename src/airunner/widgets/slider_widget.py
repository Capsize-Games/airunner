from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QLabel, QSlider


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
        self.spinbox.singleStep = val

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
        return self.spinbox.maximum

    @spinbox_maximum.setter
    def spinbox_maximum(self, val):
        self.spinbox.maximum = val

    @property
    def spinbox_minimum(self):
        return self.spinbox.minimum

    @spinbox_minimum.setter
    def spinbox_minimum(self, val):
        self.spinbox.minimum = val

    def __init__(self, *args, **kwargs):
        self.app = kwargs.pop("app", None)
        slider_minimum = kwargs.pop("slider_minimum", 0)
        slider_maximum = kwargs.pop("slider_maximum", 100)
        slider_tick_interval = kwargs.pop("slider_tick_interval", 8)
        slider_callback = kwargs.pop("slider_callback", None)
        slider_single_step = kwargs.pop("slider_single_step", 1)
        slider_page_step = kwargs.pop("slider_page_step", 1)
        spinbox_minimum = kwargs.pop("spinbox_minimum", 0)
        spinbox_maximum = kwargs.pop("spinbox_maximum", 100)
        spinbox_single_step = kwargs.pop("spinbox_single_step", 1)
        spinbox_page_step = kwargs.pop("spinbox_page_step", 1)
        label_text = kwargs.pop("label_text", "")

        super().__init__(*args, **kwargs)

        uic.loadUi("pyqt/widgets/slider.ui", self)

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
        self.slider.valueChanged.connect(lambda value: self.spinbox.setValue(value / self.slider_maximum))
        self.layout().addWidget(self.label, 0, 0, 1, 1)
        self.spinbox.lineEdit().hide()
        self.spinbox.setFixedWidth(25)
        self.spinbox.valueChanged.connect(lambda val: self.handle_slider_change(int(val * self.slider_maximum)))

    def set_stylesheet(self):
        self.slider.setStyleSheet("""
           QSlider::handle:horizontal { 
               height: 20px;
               width: 25px;
               border: 1px solid #5483d0;
               border-radius: 0px;
           }
           QSlider::handle:horizontal:hover {
               background-color: #5483d0;
           }
           QSlider::groove:horizontal {
               height: 25px;
               background-color: transparent;
               border: transparent;
               border: 1px solid #555;
               border-right: 0px;
               border-radius: 0px;
           }
           background-color: transparent;
       """)
        self.label.setStyleSheet("""
            font-size: 9pt;
            color: #ffffff;
        """)
        self.spinbox.setStyleSheet("""
            background-color: #444444;
            border-left: none;
            border-color: #555;
            border-radius: 0px;
        """)

    def handle_slider_change(self, val):
        position = val#self.slider.sliderPosition()
        single_step = self.slider.singleStep()
        adjusted_value = round(position / single_step) * single_step

        if adjusted_value < self.slider_minimum:
            adjusted_value = self.slider_minimum

        self.slider.setValue(adjusted_value)
        if self.slider_callback:
            self.slider_callback(adjusted_value)
        self.label.setText(f"{self.label_text} {str(adjusted_value)}")

    def update_value(self, val):
        self.slider.setValue(val)
        self.label.setText(f"{self.label_text} {str(val)}")

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