import pytest
from PySide6.QtWidgets import QWidget
from airunner.gui.widgets.active_grid_settings.active_grid_settings_widget import (
    ActiveGridSettingsWidget,
)


class DummyAppSettings:
    is_maximized = False
    working_height = 100
    working_width = 100  # Added to satisfy widget usage
    active_grid_size_lock = False
    dark_mode_enabled = False  # Added to satisfy is_dark property


class DummyGridSettings:
    border_opacity = 0.5
    fill_opacity = 0.5
    render_border = True
    render_fill = True
    enabled = True
    border_color = "#ff0000"
    fill_color = "#00ff00"


@pytest.fixture
def active_grid_settings_widget(qtbot, monkeypatch):
    # Patch required settings
    monkeypatch.setattr(
        ActiveGridSettingsWidget, "application_settings", DummyAppSettings()
    )
    monkeypatch.setattr(
        ActiveGridSettingsWidget, "active_grid_settings", DummyGridSettings()
    )
    widget = ActiveGridSettingsWidget()
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_active_grid_settings_happy_path(active_grid_settings_widget):
    """
    Happy path: Test initialization and state of checkboxes and sliders.
    """
    ui = active_grid_settings_widget.ui
    assert ui.active_grid_border_groupbox.isChecked()
    assert ui.active_grid_fill_groupbox.isChecked()
    assert ui.active_grid_area_checkbox.isChecked()
    assert not ui.size_lock_button.isChecked()
    assert ui.border_opacity_slider_widget.property("current_value") == 0.5
    assert ui.fill_opacity_slider_widget.property("current_value") == 0.5


def test_active_grid_settings_sad_path_toggle_checkboxes(
    active_grid_settings_widget,
):
    """
    Sad path: Toggle checkboxes and verify state changes.
    """
    ui = active_grid_settings_widget.ui
    ui.active_grid_border_groupbox.setChecked(False)
    ui.active_grid_fill_groupbox.setChecked(False)
    ui.active_grid_area_checkbox.setChecked(False)
    assert not ui.active_grid_border_groupbox.isChecked()
    assert not ui.active_grid_fill_groupbox.isChecked()
    assert not ui.active_grid_area_checkbox.isChecked()


def test_active_grid_settings_bad_path_invalid_property(
    active_grid_settings_widget,
):
    """
    Bad path: Set an invalid property and ensure no crash.
    """
    ui = active_grid_settings_widget.ui
    ui.border_opacity_slider_widget.setProperty("current_value", "not_a_float")
    assert (
        ui.border_opacity_slider_widget.property("current_value")
        == "not_a_float"
    )
