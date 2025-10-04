"""Shared filter parameter widget builder for nodes and windows."""

from typing import Callable, Optional
import logging

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QCheckBox,
    QSlider,
    QDoubleSpinBox,
    QSpinBox,
    QHBoxLayout,
)
from PySide6.QtCore import Qt

from airunner.components.art.utils.image_filter_utils import FilterValueData

LOG = logging.getLogger(__name__)


class FilterParameterWidget(QWidget):
    """Widget for a single filter parameter with appropriate input control."""

    def __init__(
        self,
        filter_value: FilterValueData,
        on_value_changed: Optional[Callable[[str, any], None]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.filter_value = filter_value
        self.on_value_changed = on_value_changed
        self._setup_ui()

    def _setup_ui(self):
        """Create the parameter widget based on value type."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Label
        label_text = self.filter_value.name.replace("_", " ").title()
        label = QLabel(label_text)
        layout.addWidget(label)

        # Control based on type
        if self.filter_value.value_type == "bool":
            self._create_bool_control(layout)
        elif self.filter_value.value_type in ("int", "float"):
            self._create_numeric_control(layout)
        else:
            # Default to text for unknown types
            LOG.warning(f"Unknown value type: {self.filter_value.value_type}")

    def _create_bool_control(self, layout: QVBoxLayout):
        """Create a checkbox for boolean values."""
        self.checkbox = QCheckBox()
        current_value = (
            self.filter_value.value == "True"
            if isinstance(self.filter_value.value, str)
            else bool(self.filter_value.value)
        )
        self.checkbox.setChecked(current_value)

        if self.on_value_changed:
            self.checkbox.stateChanged.connect(
                lambda state: self._handle_value_changed(
                    state == Qt.CheckState.Checked.value
                )
            )

        layout.addWidget(self.checkbox)

    def _create_numeric_control(self, layout: QVBoxLayout):
        """Create slider + spinbox for numeric values."""
        is_float = self.filter_value.value_type == "float"

        # Get min/max values
        min_value = (
            self.filter_value.min_value
            if self.filter_value.min_value is not None
            else 0
        )
        max_value = (
            self.filter_value.max_value
            if self.filter_value.max_value is not None
            else 100
        )

        if is_float:
            min_value = float(min_value)
            max_value = float(max_value)
            current_value = float(self.filter_value.value)
        else:
            min_value = int(min_value)
            max_value = int(max_value)
            current_value = int(self.filter_value.value)

        # Container for slider and spinbox
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(4)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        if is_float:
            # For float, use slider with 100 steps and scale
            self.slider.setMinimum(0)
            self.slider.setMaximum(100)
            self.slider.setValue(
                int(
                    (current_value - min_value) / (max_value - min_value) * 100
                )
            )
        else:
            self.slider.setMinimum(int(min_value))
            self.slider.setMaximum(int(max_value))
            self.slider.setValue(int(current_value))

        control_layout.addWidget(self.slider, stretch=3)

        # Spinbox
        if is_float:
            self.spinbox = QDoubleSpinBox()
            self.spinbox.setDecimals(2)
            self.spinbox.setSingleStep(0.01)
        else:
            self.spinbox = QSpinBox()
            self.spinbox.setSingleStep(1)

        self.spinbox.setMinimum(min_value)
        self.spinbox.setMaximum(max_value)
        self.spinbox.setValue(current_value)

        control_layout.addWidget(self.spinbox, stretch=1)
        layout.addLayout(control_layout)

        # Connect signals
        if is_float:
            self.slider.valueChanged.connect(
                lambda v: self.spinbox.setValue(
                    min_value + (v / 100.0) * (max_value - min_value)
                )
            )
            self.spinbox.valueChanged.connect(
                lambda v: self.slider.setValue(
                    int((v - min_value) / (max_value - min_value) * 100)
                )
            )
        else:
            self.slider.valueChanged.connect(self.spinbox.setValue)
            self.spinbox.valueChanged.connect(self.slider.setValue)

        if self.on_value_changed:
            self.spinbox.valueChanged.connect(self._handle_value_changed)

    def _handle_value_changed(self, value):
        """Handle value change and notify callback."""
        # Update the filter_value object
        self.filter_value.value = str(value)

        # Notify callback
        if self.on_value_changed:
            self.on_value_changed(self.filter_value.name, value)

    def get_value(self):
        """Get the current value from the widget."""
        if hasattr(self, "checkbox"):
            return self.checkbox.isChecked()
        elif hasattr(self, "spinbox"):
            return self.spinbox.value()
        return None


def create_filter_parameter_widgets(
    filter_values: list,
    on_value_changed: Optional[Callable[[str, any], None]] = None,
    parent: Optional[QWidget] = None,
) -> list:
    """
    Create a list of parameter widgets for the given filter values.

    Args:
        filter_values: List of FilterValueData objects
        on_value_changed: Callback when any parameter changes (param_name, value)
        parent: Parent widget

    Returns:
        List of FilterParameterWidget instances
    """
    widgets = []
    for fv in filter_values:
        try:
            widget = FilterParameterWidget(fv, on_value_changed, parent)
            widgets.append(widget)
        except Exception:
            LOG.exception(f"Failed to create parameter widget for {fv.name}")

    return widgets
