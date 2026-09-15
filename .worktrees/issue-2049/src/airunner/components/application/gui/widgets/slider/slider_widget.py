from decimal import Decimal, InvalidOperation
from typing import Any
from PySide6.QtCore import Slot, QTimer
from PySide6.QtWidgets import QDoubleSpinBox

from airunner.daemon_client.resource_store import TABLE_TO_RESOURCE as table_to_resource
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.application.gui.widgets.slider.templates.slider_ui import (
    Ui_slider_widget,
)


class SliderWidget(BaseWidget):
    ui: Ui_slider_widget  # type: ignore[assignment]
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
        self._callback = None

        # Setup debounce timer with a permanent connection to _process_pending_update
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(300)  # 300ms debounce delay
        self._debounce_timer.timeout.connect(self._process_pending_update)
        self._pending_update = None
        # Ensure signal connections
        self.ui.slider.valueChanged.connect(self.handle_slider_valueChanged)
        self.ui.slider.sliderReleased.connect(self.handle_slider_released)
        self.ui.slider_spinbox.valueChanged.connect(
            self.handle_spinbox_valueChanged
        )
        # Commit pending changes when the user finishes editing the spinbox.
        # This prevents races where a user types a value and immediately
        # clicks Generate before the 300ms debounce flushes to the DB.
        if hasattr(self.ui.slider_spinbox, "editingFinished"):
            self.ui.slider_spinbox.editingFinished.connect(
                self.handle_spinbox_editing_finished
            )

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
        return self.ui.slider.minimum()

    @slider_minimum.setter
    def slider_minimum(self, val):
        self.ui.slider.setMinimum(int(val))

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

    @property
    def current_value(self):
        return self.ui.slider.value()

    @Slot(int)
    def handle_slider_valueChanged(self, val):
        if self.is_loading:
            return
        position = val
        single_step = self.ui.slider.singleStep()
        adjusted_value = round(position / single_step) * single_step
        if adjusted_value < self.slider_minimum:
            adjusted_value = self.slider_minimum
        if self.ui.slider.value() != adjusted_value:
            self.ui.slider.blockSignals(True)
            self.ui.slider.setValue(adjusted_value)
            self.ui.slider.blockSignals(False)
        try:
            normalized = (adjusted_value - self.slider_minimum) / (
                self.slider_maximum - self.slider_minimum
            )
            spinbox_val = (
                normalized * (self.spinbox_maximum - self.spinbox_minimum)
                + self.spinbox_minimum
            )
        except ZeroDivisionError:
            spinbox_val = self.spinbox_minimum
        spinbox_val = round(spinbox_val, 4)
        if abs(self.ui.slider_spinbox.value() - spinbox_val) > 1e-6:
            self.ui.slider_spinbox.blockSignals(True)
            self.ui.slider_spinbox.setValue(spinbox_val)
            self.ui.slider_spinbox.blockSignals(False)
        # Do NOT call self.slider_callback here. Only update UI.

    @Slot()
    def handle_slider_released(self):
        if self.is_loading:
            return
        # Slider release is already a natural debounce boundary.
        # Commit immediately so downstream actions (e.g., Generate) don't race
        # against the 300ms debounce timer and read stale settings.
        if not self.settings_property:
            return
        if self._callback:
            self._callback(self.settings_property, self.current_value)
            return

        self._debounce_timer.stop()
        self._pending_update = (self.settings_property, self.current_value)
        self._process_pending_update()

    @Slot(float)
    def handle_spinbox_valueChanged(self, val: float):
        try:
            normalized = (val - self.spinbox_minimum) / (
                self.spinbox_maximum - self.spinbox_minimum
            )
            slider_val = round(
                normalized * (self.slider_maximum - self.slider_minimum)
                + self.slider_minimum
            )
        except ZeroDivisionError:
            slider_val = self.slider_minimum
        if self.ui.slider.value() != slider_val:
            self.ui.slider.blockSignals(True)
            self.ui.slider.setValue(slider_val)
            self.ui.slider.blockSignals(False)
        self.slider_callback(self.settings_property, slider_val)

    @Slot()
    def handle_spinbox_editing_finished(self):
        if self.is_loading:
            return
        if not self.settings_property:
            return

        slider_val = self.ui.slider.value()

        # If a custom callback is configured, let it handle persistence.
        if self._callback:
            self._callback(self.settings_property, slider_val)
            return

        # Otherwise, flush the debounced update immediately.
        self._debounce_timer.stop()
        self._pending_update = (self.settings_property, slider_val)
        self._process_pending_update()

    def showEvent(self, event):
        self.init()
        super().showEvent(event)

    @staticmethod
    def _spinbox_decimal_places(step_value: Any) -> int:
        """Return the configured fractional digits for one step value."""
        try:
            exponent = Decimal(str(step_value)).normalize().as_tuple().exponent
        except InvalidOperation:
            return 0
        return abs(exponent) if exponent < 0 else 0

    def init(self, **kwargs):
        self.is_loading = True
        self._callback = kwargs.get("slider_callback", None)
        if self._callback is None:
            self._callback = self.property("slider_callback") or None
        slider_minimum = kwargs.get(
            "slider_minimum", self.property("slider_minimum") or 0
        )
        slider_maximum = kwargs.get(
            "slider_maximum", self.property("slider_maximum") or 100
        )
        spinbox_minimum = kwargs.get(
            "spinbox_minimum", self.property("spinbox_minimum") or 0.0
        )
        spinbox_maximum = kwargs.get(
            "spinbox_maximum", self.property("spinbox_maximum") or 100.0
        )
        current_value = None
        settings_property = kwargs.get(
            "settings_property", self.property("settings_property") or None
        )
        self.table_id = self.property("table_id") or None
        if self.table_id is not None:
            self.table_name, self.table_column = settings_property.split(".")
        label_text = kwargs.get(
            "label_text", self.property("label_text") or ""
        )
        display_as_float = kwargs.get(
            "display_as_float", self.property("display_as_float") or False
        )

        slider_tick_interval = self.property("slider_tick_interval") or 8
        slider_single_step = self.property("slider_single_step") or 1
        slider_page_step = self.property("slider_page_step") or 1

        spinbox_single_step = self.property("spinbox_single_step") or 0.01
        spinbox_page_step = self.property("spinbox_page_step") or 0.01

        slider_name = self.property("slider_name") or None
        spinbox_name = self.property("spinbox_name") or None

        divide_by = self.property("divide_by") or 1.0

        if (
            self.table_id is not None
            and self.table_name is not None
            and self.table_column is not None
        ):
            resource_name = table_to_resource.get(self.table_name)
            if resource_name is not None:
                self.table_item = self.resource_store.get(
                    resource_name,
                    int(self.table_id),
                )
                current_value = getattr(
                    self.table_item,
                    self.table_column,
                    None,
                )

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

        if label_text != "":
            self.ui.groupBox.setTitle(label_text)
            self.ui.groupBox.setStyleSheet("")  # Reset to default
        else:
            # Hide border and remove padding if label_text is empty
            self.ui.groupBox.setTitle("")
            self.ui.groupBox.setStyleSheet(
                "QGroupBox { border: none; padding: 0px; margin-top: 0px; }"
            )

        self.set_slider_and_spinbox_values(current_value)
        if not self.display_as_float:
            self.ui.slider_spinbox.setDecimals(0)
        else:
            decimals = self._spinbox_decimal_places(spinbox_single_step)
            self.ui.slider_spinbox.setDecimals(2 if decimals < 2 else decimals)

        self.is_loading = False

    def slider_callback(self, attr_name, value=None):
        """
        Slider widget callback - this is connected via dynamic properties in the
        qt widget. This function is then called when the value of a SliderWidget
        is changed.
        :param attr_name: the name of the attribute to change
        :param value: the value to set the attribute to
        :return:
        """
        if not attr_name:
            return
        if self._callback:
            self._callback(attr_name, value)
        else:
            self.set_settings_value(attr_name, value)

    def get_settings_value(self, settings_property):
        if self.table_item is not None:
            # If we already have an item from the table, we can get the value
            # directly from it
            return getattr(self.table_item, self.table_column, None)

        # If a single name is passed, we assume it's a column name
        # in the application_settings table
        keys = settings_property.split(".")
        if len(keys) == 1:
            keys = ["application_settings", keys[0]]

        table_name = keys[0]
        column_name = keys[1]

        resource_name = table_to_resource.get(table_name)
        if resource_name is None:
            self.logger.error(
                f"No resource mapping found for table: {table_name}"
            )
            return None

        if self.table_id:
            obj = self.resource_store.get(resource_name, int(self.table_id))
        else:
            if self.resource_store.is_singleton(resource_name):
                obj = self.resource_store.get_singleton(resource_name)
            else:
                obj = self.resource_store.first(resource_name)

        # Check if we have an object
        if obj is None:
            self.logger.error(
                f"Object {table_name} is None for settings_property: {settings_property}"
            )
            return

        # Return the value of the column
        return getattr(obj, column_name, None)

    def set_settings_value(self, settings_property: str, val: Any):
        # Store the current update parameters for the timer callback
        self._pending_update = (settings_property, val)

        # Cancel any existing timer to reset the debounce period
        self._debounce_timer.stop()

        # Start a new timer that will trigger the actual update when it expires
        self._debounce_timer.start()

    def _process_pending_update(self):
        """Execute the actual update after the debounce period has elapsed."""
        # Get the latest pending update
        if self._pending_update:
            settings_property, val = self._pending_update
            self._pending_update = None

            if self.table_item is not None:
                setattr(self.table_item, self.table_column, val)
                resource_name = table_to_resource.get(self.table_name)
                if resource_name is not None:
                    values = getattr(
                        self.table_item,
                        "to_dict",
                        lambda: dict(self.table_item.__dict__),
                    )()
                    values.pop("id", None)
                    values.pop("_sa_instance_state", None)
                    self.resource_store.update(
                        resource_name,
                        self.table_item.id,
                        values,
                    )
            elif settings_property is not None:
                keys = settings_property.split(".")
                self.update_setting_by_table_name(
                    table_name=keys[0], column_name=keys[1], val=val
                )

    def set_slider_and_spinbox_values(self, val):
        if val is None:
            val = 0
        if self.slider_maximum == 0:
            normalized = 0
        else:
            normalized = val / self.slider_maximum
        spinbox_val = normalized * self.spinbox_maximum
        spinbox_val = round(spinbox_val, 2)

        self.ui.slider.blockSignals(True)
        self.ui.slider_spinbox.blockSignals(True)
        self.ui.slider.setValue(int(val))
        self.ui.slider_spinbox.setValue(spinbox_val)
        self.ui.slider.blockSignals(False)
        self.ui.slider_spinbox.blockSignals(False)

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

    def set_label(self, label_text: str):
        """Set the label text for the slider widget."""
        if hasattr(self.ui, "groupBox"):
            self.ui.groupBox.setTitle(label_text)
            if label_text:
                self.ui.groupBox.setStyleSheet("")  # Reset to default
            else:
                self.ui.groupBox.setStyleSheet(
                    "QGroupBox { border: none; padding: 0px; margin-top: 0px; }"
                )

    def set_minimum(self, val: float):
        """Set minimum value for both slider and spinbox."""
        self.slider_minimum = int(val) if not self.display_as_float else val
        self.spinbox_minimum = val

    def set_maximum(self, val: float):
        """Set maximum value for both slider and spinbox."""
        self.slider_maximum = int(val) if not self.display_as_float else val
        self.spinbox_maximum = val

    def set_step_size(self, val: float):
        """Set step size for both slider and spinbox."""
        self.slider_single_step = (
            int(val) if not self.display_as_float else val
        )
        self.slider_page_step = int(val) if not self.display_as_float else val
        self.spinbox_single_step = val
        self.spinbox_page_step = val

    def set_value(self, val: float):
        """Set the current value of the slider and spinbox."""
        self.is_loading = True
        self.set_slider_and_spinbox_values(val)
        self.is_loading = False

    def set_display_as_float(self, display_as_float: bool):
        """Set whether to display values as float."""
        self.display_as_float = display_as_float
        if not display_as_float:
            self.ui.slider_spinbox.setDecimals(0)
        else:
            self.ui.slider_spinbox.setDecimals(4)

    def value(self) -> float:
        """Get the current value from the spinbox."""
        return self.ui.slider_spinbox.value()
