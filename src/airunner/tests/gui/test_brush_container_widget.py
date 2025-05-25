import pytest
from PySide6.QtWidgets import QColorDialog
from airunner.gui.widgets.brush.brush_container_widget import (
    BrushContainerWidget,
)


class DummyBrushSettings:
    size = 10
    primary_color = "#123456"


class DummyDrawingPadSettings:
    enable_automatic_drawing = True


class DummyAPI:
    class Canvas:
        def brush_color_changed(self, color):
            self.last_color = color

    class Art:
        def __init__(self):
            self.canvas = DummyAPI.Canvas()

    def __init__(self):
        self.art = DummyAPI.Art()


def dummy_update_brush_settings(key, value):
    dummy_update_brush_settings.called = (key, value)


def dummy_update_drawing_pad_settings(key, value):
    dummy_update_drawing_pad_settings.called = (key, value)


class TestBrushContainerWidget(BrushContainerWidget):
    def __init__(
        self, brush_settings, drawing_pad_settings, api, *args, **kwargs
    ):
        self._test_brush_settings = brush_settings
        self._test_drawing_pad_settings = drawing_pad_settings
        self._test_api = api
        super().__init__(*args, **kwargs)

    @property
    def brush_settings(self):
        return self._test_brush_settings

    @brush_settings.setter
    def brush_settings(self, value):
        self._test_brush_settings = value

    @property
    def drawing_pad_settings(self):
        return self._test_drawing_pad_settings

    @drawing_pad_settings.setter
    def drawing_pad_settings(self, value):
        self._test_drawing_pad_settings = value

    @property
    def api(self):
        return self._test_api

    @api.setter
    def api(self, value):
        self._test_api = value


@pytest.fixture
def brush_container_widget(qtbot):
    widget = TestBrushContainerWidget(
        DummyBrushSettings(), DummyDrawingPadSettings(), DummyAPI()
    )
    widget.update_brush_settings = dummy_update_brush_settings
    widget.update_drawing_pad_settings = dummy_update_drawing_pad_settings
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_brush_container_happy_path(brush_container_widget):
    """
    Happy path: Test initial state and color button style.
    """
    ui = brush_container_widget.ui
    assert ui.brush_size_slider.property("current_value") == 10
    assert ui.primary_color_button.styleSheet() == "background-color: #123456;"
    assert ui.toggle_auto_generate_while_drawing.isChecked()


def test_brush_container_sad_path_toggle_auto_generate(brush_container_widget):
    """
    Sad path: Toggle auto-generate and check update method is called.
    """
    brush_container_widget.toggle_auto_generate_while_drawing(False)
    assert dummy_update_drawing_pad_settings.called == (
        "enable_automatic_drawing",
        False,
    )


def test_brush_container_bad_path_invalid_color(
    brush_container_widget, monkeypatch
):
    """
    Bad path: Simulate color dialog returning invalid color.
    """

    class DummyColor:
        def isValid(self):
            return False

        def name(self):
            return "#000000"

    monkeypatch.setattr(QColorDialog, "getColor", lambda *a, **k: DummyColor())
    brush_container_widget.color_button_clicked()
    # Should not update color or crash
    assert not hasattr(dummy_update_brush_settings, "called")
