"""Regression tests for slider widget decimal configuration."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.application.gui.widgets.slider.slider_widget import (
    SliderWidget,
)


def test_spinbox_decimal_places_handles_integer_steps():
    """Integer step sizes should not be treated as malformed floats."""
    assert SliderWidget._spinbox_decimal_places(1) == 0
    assert SliderWidget._spinbox_decimal_places("1") == 0


def test_init_accepts_integer_float_spinbox_step():
    """Float-display sliders should tolerate integer single-step values."""
    properties = {
        "display_as_float": True,
        "spinbox_single_step": 1,
    }
    widget = SimpleNamespace(
        _callback=None,
        table_item=None,
        table_id=None,
        table_name=None,
        table_column=None,
        ui=SimpleNamespace(
            slider=SimpleNamespace(setObjectName=Mock()),
            slider_spinbox=SimpleNamespace(
                setObjectName=Mock(),
                setDecimals=Mock(),
            ),
            groupBox=SimpleNamespace(
                setTitle=Mock(),
                setStyleSheet=Mock(),
            ),
        ),
        property=lambda name: properties.get(name),
        get_settings_value=lambda _name: 0,
        set_slider_and_spinbox_values=Mock(),
        _spinbox_decimal_places=SliderWidget._spinbox_decimal_places,
        is_loading=False,
    )

    SliderWidget.init(widget)

    widget.ui.slider_spinbox.setDecimals.assert_called_once_with(2)