from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QDoubleSpinBox

from airunner.enums import SignalCode, ServiceCode
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
        self.ui.slider.setSingleStep(int(val))

    @property
    def slider_page_step(self):
        return self.ui.slider.pageStep()

    @slider_page_step.setter
    def slider_page_step(self, val):
        self.ui.slider.setPageStep(int(val))

    @property
    def spinbox_single_step(self):
        return self.ui.slider_spinbox.singleStep

    @spinbox_single_step.setter
    def spinbox_single_step(self, val):
        self.ui.slider_spinbox.setSingleStep(val)

    @property
    def is_double_spin_box(self):
        return type(self.ui.slider_spinbox) == QDoubleSpinBox

    @property
    def spinbox_page_step(self):
        if self.is_double_spin_box:
            return self.spinbox_single_step
        return self.ui.slider_spinbox.pageStep

    @spinbox_page_step.setter
    def spinbox_page_step(self, val):
        if self.is_double_spin_box:
            self.spinbox_single_step = val
        else:
            self.ui.slider_spinbox.pageStep = val

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
        self.ui.slider.minimum = int(val)

    @property
    def slider_maximum(self):
        return self.ui.slider.maximum()

    @slider_maximum.setter
    def slider_maximum(self, val):
        self.ui.slider.setMaximum(int(val))

    @property
    def spinbox_maximum(self):
        return self.ui.slider_spinbox.maximum()

    @spinbox_maximum.setter
    def spinbox_maximum(self, val):
        self.ui.slider_spinbox.setMaximum(val)

    @property
    def spinbox_minimum(self):
        return self.ui.slider_spinbox.minimum()

    @spinbox_minimum.setter
    def spinbox_minimum(self, val):
        self.ui.slider_spinbox.setMinimum(val)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.slider_callback = None
        self.label_text = None
        self.settings_property = None
        self.label = None
        self.register(SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL, self.on_main_window_loaded_signal)
    
    def on_main_window_loaded_signal(self):
        self.init()

    def settings_loaded(self, callback):
        self.init(slider_callback=callback)
    
    def init(self, **kwargs):
        slider_callback = kwargs.get("slider_callback", self.property("slider_callback") or None)
        slider_minimum = kwargs.get("slider_minimum", self.property("slider_minimum") or 0)
        slider_maximum = kwargs.get("slider_maximum", self.property("slider_maximum") or 100)
        spinbox_minimum = kwargs.get("spinbox_minimum", self.property("spinbox_minimum") or 0.0)
        spinbox_maximum = kwargs.get("spinbox_maximum", self.property("spinbox_maximum") or 100.0)
        current_value = kwargs.get("current_value", self.property("current_value") or 0)
        settings_property = kwargs.get("settings_property", self.property("settings_property") or None)
        label_text = kwargs.get("label_text", self.property("label_text") or "")
        display_as_float = kwargs.get("display_as_float", self.property("display_as_float") or False)

        slider_tick_interval = self.property("slider_tick_interval") or 8
        slider_single_step = self.property("slider_single_step") or 1
        slider_page_step = self.property("slider_page_step") or 1

        spinbox_single_step = self.property("spinbox_single_step") or 0.01
        spinbox_page_step = self.property("spinbox_page_step") or 0.01

        slider_name = self.property("slider_name") or None
        spinbox_name = self.property("spinbox_name") or None

        divide_by = self.property("divide_by") or 1.0

        if settings_property is not None:
            current_value = self.get_settings_value(settings_property)

        # check if slider_callback is str
        if isinstance(slider_callback, str):
            slider_callback = self.handle_value_change

        # set slider and spinbox names
        if slider_name:
            self.ui.slider.setObjectName(slider_name)

        if spinbox_name:
            self.ui.slider_spinbox.setObjectName(spinbox_name)

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
        self.settings_property = settings_property
        self.display_as_float = display_as_float
        self.divide_by = divide_by

        self.label = QLabel(f"{label_text}")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.label.setObjectName("slider_label")
        #self.ui.slider.valueChanged.connect(lambda value: self.ui.slider_spinbox.setValue(value / self.slider_maximum))
        # add the label to the ui
        self.layout().addWidget(self.label, 0, 0, 1, 1)
        # self.ui.slider_spinbox.lineEdit().hide()
        self.ui.slider_spinbox.setFixedWidth(50)
        self.ui.slider_spinbox.valueChanged.connect(self.handle_spinbox_change)
        self.ui.slider.valueChanged.connect(self.handle_slider_change)
        self.set_slider_and_spinbox_values(current_value)
        if not self.display_as_float:
            self.ui.slider_spinbox.setDecimals(0)
        else:
            decimals = len(str(spinbox_single_step).split(".")[1])
            self.ui.slider_spinbox.setDecimals(2 if decimals < 2 else decimals)

    def handle_value_change(self, attr_name, value=None, widget=None):
        """
        Slider widget callback - this is connected via dynamic properties in the
        qt widget. This function is then called when the value of a SliderWidget
        is changed.
        :param attr_name: the name of the attribute to change
        :param value: the value to set the attribute to
        :param widget: the widget that triggered the callback
        :return:
        """
        if attr_name is None:
            return

        keys = attr_name.split(".")
        if len(keys) > 0:
            settings = self.settings

            object_key = "settings"
            property_key = None
            sub_property_key = None
            if len(keys) == 1:
                property_key = keys[0]
            elif len(keys) == 2:
                object_key = keys[0]
                property_key = keys[1]
            elif len(keys) == 3:
                object_key = keys[0]
                property_key = keys[1]
                sub_property_key = keys[2]

            if property_key and sub_property_key:
                if object_key != "settings":
                    if len(keys) == 3:
                        settings[object_key][property_key][sub_property_key] = value
                    else:
                        settings[object_key][property_key] = value
                else:
                    settings[property_key] = value

                self.settings = settings

    def get_settings_value(self, settings_property):
        keys = settings_property.split(".")
        data = self.settings

        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return None

        return data

    def set_slider_and_spinbox_values(self, val):
        if val is None:
            val = 0

        self.ui.slider.blockSignals(True)
        self.ui.slider_spinbox.blockSignals(True)

        single_step = self.ui.slider.singleStep()
        adjusted_value = val
        if single_step > 0:
            val = float(val)
            single_step = float(single_step)
            adjusted_value = round(val / single_step) * single_step
        normalized = adjusted_value / self.slider_maximum
        spinbox_val = normalized * self.spinbox_maximum
        spinbox_val = round(spinbox_val, 2)
        self.ui.slider_spinbox.setValue(spinbox_val)

        self.ui.slider.setValue(int(val))
        self.ui.slider_spinbox.setValue(spinbox_val)

        self.ui.slider.blockSignals(False)
        self.ui.slider_spinbox.blockSignals(False)

    @property
    def current_value(self):
        return self.ui.slider.value()

    def handle_spinbox_change(self, val):
        normalized = val / self.spinbox_maximum
        slider_val = normalized * self.slider_maximum
        self.ui.slider.setValue(round(slider_val))
        # self.update_label()

    def handle_slider_change(self, val):
        position = val#self.ui.slider.sliderPosition()
        single_step = self.ui.slider.singleStep()
        adjusted_value = round(position / single_step) * single_step
        if adjusted_value < self.slider_minimum:
            adjusted_value = self.slider_minimum
        self.ui.slider.setValue(int(adjusted_value))

        try:
            normalized = adjusted_value / self.slider_maximum
            spinbox_val = normalized * self.spinbox_maximum
        except ZeroDivisionError:
            spinbox_val = 0.0
        spinbox_val = round(spinbox_val, 2)
        self.ui.slider_spinbox.setValue(spinbox_val)

        # self.update_label()
        if self.slider_callback:
            self.slider_callback(self.settings_property, adjusted_value)

    def update_value(self, val):
        self.ui.slider.setValue(int(val))

        if self.display_as_float:
            val = self.ui.slider_spinbox.value()

        # self.update_label()

    # def update_label(self):
    #     if self.display_as_float:
    #         val = f"{self.ui.slider_spinbox.value():.2f}"
    #     else:
    #         val = f"{int(self.ui.slider_spinbox.value())}"
    #     self.label.setText(f"{self.label_text} {val}")

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

    def setValue(self, val):
        self.ui.slider.setValue(val)