import pytest
from PySide6.QtWidgets import QColorDialog
from pytestqt.qt_compat import qt_api

from airunner.gui.widgets.color_picker import ColorPicker


@pytest.fixture
def color_picker_widget(qtbot):
    """
    Fixture to create a ColorPicker instance for testing.
    """
    widget = ColorPicker()
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_color_picker_initial_state(color_picker_widget):
    """
    Test the initial state of the ColorPicker widget.
    """
    assert isinstance(color_picker_widget, QColorDialog)
    assert color_picker_widget.isVisible()
    # Should have NoButtons and DontUseNativeDialog options set
    options = color_picker_widget.options()
    assert options & QColorDialog.ColorDialogOption.NoButtons
    assert options & QColorDialog.ColorDialogOption.DontUseNativeDialog


def test_color_picker_select_color(qtbot, color_picker_widget):
    """
    Test selecting a color programmatically and ensure the color is set.
    """
    from PySide6.QtGui import QColor

    test_color = QColor(100, 150, 200)
    color_picker_widget.setCurrentColor(test_color)
    assert color_picker_widget.currentColor() == test_color

    # Simulate user picking a new color (simulate signal)
    new_color = QColor(10, 20, 30)
    color_picker_widget.setCurrentColor(new_color)
    assert color_picker_widget.currentColor() == new_color


def test_color_picker_bad_path_invalid_color(color_picker_widget):
    """
    Test setting an invalid color (bad path).
    Should reset to black (QColor(0,0,0)) or not crash.
    """
    from PySide6.QtGui import QColor

    color_picker_widget.setCurrentColor("not a color")
    # The color should be black
    assert color_picker_widget.currentColor() == QColor(0, 0, 0)
