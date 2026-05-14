"""Regression tests for STT settings widget wiring."""

from unittest.mock import Mock

from airunner.components.stt.gui.widgets.whisper_settings_widget import (
    WhisperSettingsWidget,
)


def test_stt_settings_ui_imports_without_missing_subpackage():
    """The generated STT settings UI should import cleanly."""
    from airunner.components.stt.gui.widgets.templates.stt_settings_ui import (
        Ui_stt_settings,
    )

    assert Ui_stt_settings is not None


def test_whisper_settings_widget_task_change_uses_selected_text():
    """Task updates should persist the selected combobox text."""
    widget = WhisperSettingsWidget.__new__(WhisperSettingsWidget)
    widget.update_whisper_settings = Mock()

    WhisperSettingsWidget.on_task_changed(widget, "translate")

    widget.update_whisper_settings.assert_called_once_with(
        task="translate"
    )