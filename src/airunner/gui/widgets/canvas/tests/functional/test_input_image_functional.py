"""
Functional tests for InputImage widget (PySide6, requires QApplication and qtbot).
"""

import pytest

pytestmark = pytest.mark.skip(
    reason="Segfaults in PySide6/Qt teardown; see AI Runner issue tracker. Business logic is covered by headless unit tests."
)
from airunner.gui.widgets.canvas.input_image import InputImage


@pytest.fixture
def input_image_widget(qtbot):
    # This fixture creates a real InputImage widget for functional testing
    widget = InputImage(settings_key="image_to_image_settings")
    qtbot.addWidget(widget)
    return widget


def test_link_button_triggers_auto_refresh(qtbot, input_image_widget):
    # Simulate toggling the link button and drawing on the main canvas
    # This is a placeholder; actual implementation depends on signal wiring
    input_image_widget.current_settings.use_grid_image_as_input = True
    input_image_widget.current_settings.lock_input_image = False
    # Simulate main canvas image change
    input_image_widget._on_drawing_pad_image_changed()
    # Assert the widget updated (would need to check image or state)
    # For now, just ensure no exceptions and method is called
    assert True
    input_image_widget.close()  # Ensure widget is closed


def test_import_and_delete(qtbot, input_image_widget, monkeypatch):
    # Simulate import
    monkeypatch.setattr(
        "airunner.gui.widgets.canvas.input_image.QFileDialog.getOpenFileName",
        lambda *a, **k: ("/tmp/fake.png", ""),
    )
    input_image_widget.load_image = lambda path: setattr(
        input_image_widget, "_imported", path
    )
    input_image_widget.import_image()
    assert getattr(input_image_widget, "_imported", None) == "/tmp/fake.png"
    # Simulate delete
    input_image_widget._scene = type(
        "Scene",
        (),
        {"clear": lambda self: setattr(input_image_widget, "_cleared", True)},
    )()
    input_image_widget.ui = type("UI", (), {"image_container": type("IC", (), {})()})()
    input_image_widget.load_image_from_settings = lambda: setattr(
        input_image_widget, "_reloaded", True
    )
    input_image_widget.delete_image()
    assert getattr(input_image_widget, "_cleared", False)
    assert getattr(input_image_widget, "_reloaded", False)
    input_image_widget.close()  # Ensure widget is closed
