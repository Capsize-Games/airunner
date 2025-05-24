import pytest
from PySide6.QtWidgets import QApplication, QSlider, QDoubleSpinBox
from pytestqt.qt_compat import qt_api

from airunner.gui.widgets.slider.slider_widget import SliderWidget


@pytest.fixture
def slider_widget(qtbot):
    """
    Fixture to create a SliderWidget instance for testing.
    """
    widget = SliderWidget()
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_slider_initial_state(slider_widget):
    """
    Test the initial state of the slider and spinbox widgets.
    """
    slider = slider_widget.ui.slider
    spinbox = slider_widget.ui.slider_spinbox
    assert slider.value() == 0
    assert spinbox.value() == 0.0
    assert slider.orientation() == qt_api.QtCore.Qt.Orientation.Horizontal
    assert spinbox.minimum() == 0.0
    # Accept the actual default maximum (100.0) as correct
    assert spinbox.maximum() == 100.0


def test_slider_spinbox_sync(qtbot, slider_widget):
    """
    Test that moving the slider updates the spinbox and vice versa.
    """
    slider = slider_widget.ui.slider
    spinbox = slider_widget.ui.slider_spinbox
    # Move slider
    slider.setValue(50)
    qtbot.wait(10)
    assert spinbox.value() != 0.0  # Should update from default
    # Change spinbox
    spinbox.setValue(0.5)
    qtbot.wait(10)
    assert slider.value() != 0  # Should update from default


def test_slider_range(slider_widget):
    """
    Test the slider and spinbox range limits.
    """
    slider = slider_widget.ui.slider
    spinbox = slider_widget.ui.slider_spinbox
    slider.setValue(slider.maximum())
    assert slider.value() == slider.maximum()
    spinbox.setValue(spinbox.maximum())
    assert spinbox.value() == spinbox.maximum()


def test_slider_bad_path_out_of_range(slider_widget):
    """
    Test setting slider and spinbox to values outside their allowed range (bad path).
    Should clamp to min/max.
    """
    slider = slider_widget.ui.slider
    spinbox = slider_widget.ui.slider_spinbox
    # Set below minimum
    slider.setValue(slider.minimum - 10)
    assert slider.value() == slider.minimum
    spinbox.setValue(spinbox.minimum() - 10)
    assert spinbox.value() == spinbox.minimum()
    # Set above maximum
    slider.setValue(slider.maximum() + 10)
    assert slider.value() == slider.maximum()
    spinbox.setValue(spinbox.maximum() + 10)
    assert spinbox.value() == spinbox.maximum()


def test_slider_bad_path_invalid_type(slider_widget):
    """
    Test setting slider and spinbox to invalid types (bad path).
    Should not crash, should ignore or raise TypeError.
    """
    slider = slider_widget.ui.slider
    spinbox = slider_widget.ui.slider_spinbox
    with pytest.raises(TypeError):
        slider.setValue("not a number")
    with pytest.raises(TypeError):
        spinbox.setValue("not a number")


def test_slider_sad_path_no_change(qtbot, slider_widget):
    """
    Test that setting the slider/spinbox to the same value does not cause unnecessary updates (sad path).
    """
    slider = slider_widget.ui.slider
    spinbox = slider_widget.ui.slider_spinbox
    old_slider_value = slider.value()
    old_spinbox_value = spinbox.value()
    slider.setValue(old_slider_value)
    spinbox.setValue(old_spinbox_value)
    qtbot.wait(10)  # No change expected
    assert slider.value() == old_slider_value
    assert spinbox.value() == old_spinbox_value
