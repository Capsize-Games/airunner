from typing import Any
from PySide6.QtCore import Slot
from PySide6.QtWidgets import QDoubleSpinBox

from airunner.data.models.settings_models import Lora
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.slider.templates.slider_ui import Ui_slider_widget


class SliderWidget(BaseWidget):
    widget_class_ = Ui_slider_widget
    display_as_float = False
    divide_by = 1.0
    is_loading = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings_property = None
        self.table_id = None
        self.table_name = None
        self.table_column = None
        self.table_item = None
        self.ui.slider.sliderReleased.connect(self.handle_slider_release)  # Connect valueChanged signal
        self.ui.slider_spinbox.valueChanged.connect(self.handle_spinbox_change)  # Connect valueChanged signal
        self._callback = None

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

    def showEvent(self, event):
        self.init()
        super().showEvent(event)

    def init(self, **kwargs):
        self.is_loading = True
        self._callback = kwargs.get("slider_callback", None)
        if self._callback is None:
            self._callback = self.property("slider_callback") or None
        slider_minimum = kwargs.get("slider_minimum", self.property("slider_minimum") or 0)
        slider_maximum = kwargs.get("slider_maximum", self.property("slider_maximum") or 100)
        spinbox_minimum = kwargs.get("spinbox_minimum", self.property("spinbox_minimum") or 0.0)
        spinbox_maximum = kwargs.get("spinbox_maximum", self.property("spinbox_maximum") or 100.0)
        current_value = None
        settings_property = kwargs.get("settings_property", self.property("settings_property") or None)
        self.table_id = self.property("table_id") or None
        if self.table_id is not None:
            self.table_name, self.table_column = settings_property.split(".")
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

        if self.table_id is not None and self.table_name is not None and self.table_column is not None:
            session = self.db_handler.get_db_session()
            if self.table_name == "lora":
                self.table_item = session.query(Lora).filter_by(id=self.table_id).first()
                current_value = getattr(self.table_item, self.table_column)
            session.close()
        elif current_value is None:
            if settings_property is not None:
                current_value = self.get_settings_value(settings_property)
            else:
                current_value = 0

        # set slider and spinbox names
        if slider_name:
            self.ui.slider.setObjectName(slider_name)

        if spinbox_name:
            self.ui.slider_spinbox.setObjectName(spinbox_name)

        self.slider_maximum = slider_maximum
        self.slider_minimum = slider_minimum
        self.slider_tick_interval = slider_tick_interval
        self.slider_single_step = slider_single_step
        self.slider_page_step = slider_page_step
        self.spinbox_single_step = spinbox_single_step
        self.spinbox_page_step = spinbox_page_step
        self.spinbox_minimum = spinbox_minimum
        self.spinbox_maximum = spinbox_maximum
        self.settings_property = settings_property
        self.display_as_float = display_as_float
        self.divide_by = divide_by

        self.ui.groupBox.setTitle(label_text)

        # add the label to the ui
        self.ui.slider_spinbox.setFixedWidth(50)
        self.set_slider_and_spinbox_values(current_value)
        if not self.display_as_float:
            self.ui.slider_spinbox.setDecimals(0)
        else:
            decimals = len(str(spinbox_single_step).split(".")[1])
            self.ui.slider_spinbox.setDecimals(2 if decimals < 2 else decimals)

        self.is_loading = False

    def slider_callback(self, attr_name, value=None, widget=None):
        """
        Slider widget callback - this is connected via dynamic properties in the
        qt widget. This function is then called when the value of a SliderWidget
        is changed.
        :param attr_name: the name of the attribute to change
        :param value: the value to set the attribute to
        :param widget: the widget that triggered the callback
        :return:
        """
        if self._callback:
            self._callback(attr_name, value)
        else:
            self.set_settings_value(attr_name, value)

    def get_settings_value(self, settings_property):
        if self.table_item is not None:
            return getattr(self.table_item, self.table_column)
        keys = settings_property.split(".")

        if len(keys) == 1:
            keys = ["application_settings", keys[0]]

        obj = getattr(self, keys[0])

        if keys[0] == "llm_generator_settings":
            return getattr(obj, keys[2])

        return getattr(obj, keys[1])

    def set_settings_value(self, settings_property: str, val: Any):
        if self.table_item is not None:
            session = self.db_handler.get_db_session()
            setattr(self.table_item, self.table_column, val)
            session.add(self.table_item)
            session.commit()
            session.close()
        elif settings_property is not None:
            keys = settings_property.split(".")
            self.update_settings_by_name(keys[0], keys[1], val)

    def set_slider_and_spinbox_values(self, val):
        if val is None:
            val = 0

        normalized = val / self.slider_maximum
        spinbox_val = normalized * self.spinbox_maximum
        spinbox_val = round(spinbox_val, 2)

        self.ui.slider.blockSignals(True)
        self.ui.slider_spinbox.blockSignals(True)
        self.ui.slider.setValue(int(val))
        self.ui.slider_spinbox.setValue(spinbox_val)
        self.ui.slider.blockSignals(False)
        self.ui.slider_spinbox.blockSignals(False)

    @property
    def current_value(self):
        return self.ui.slider.value()

    def handle_spinbox_change(self, val):
        normalized = val / self.spinbox_maximum
        slider_val = round(normalized * self.slider_maximum)
        self.ui.slider.blockSignals(True)
        self.ui.slider.setValue(slider_val)
        self.ui.slider.blockSignals(False)
        self.slider_callback(self.settings_property, slider_val)

    @Slot(int)
    def handle_slider_change(self, val):
        if self.is_loading:
            return
        position = val
        single_step = self.ui.slider.singleStep()
        adjusted_value = round(position / single_step) * single_step
        if adjusted_value < self.slider_minimum:
            adjusted_value = self.slider_minimum

        self.ui.slider.blockSignals(True)
        self.ui.slider.setValue(adjusted_value)
        self.ui.slider.blockSignals(False)

        try:
            normalized = adjusted_value / self.slider_maximum
            spinbox_val = normalized * self.spinbox_maximum
        except ZeroDivisionError:
            spinbox_val = 0.0

        spinbox_val = round(spinbox_val, 2)
        self.ui.slider_spinbox.blockSignals(True)
        self.ui.slider_spinbox.setValue(spinbox_val)
        self.ui.slider_spinbox.blockSignals(False)

    @Slot()
    def handle_slider_release(self):
        if self.is_loading:
            return
        if self.slider_callback:
            self.slider_callback(self.settings_property, self.current_value)

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

    def closeEvent(self, event):
        self.ui.slider.sliderReleased.disconnect(self.handle_slider_release)
        self.ui.slider.valueChanged.disconnect(self.handle_slider_change)
        self.ui.slider_spinbox.valueChanged.disconnect(self.handle_spinbox_change)
        super().closeEvent(event)
