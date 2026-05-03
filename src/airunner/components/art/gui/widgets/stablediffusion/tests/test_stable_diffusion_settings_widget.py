"""Tests for StableDiffusionSettingsWidget startup behavior."""

from unittest.mock import Mock, patch

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.widgets.stablediffusion.stable_diffusion_settings_widget import (  # noqa: E501
    StableDiffusionSettingsWidget,
)


def test_finish_deferred_startup_is_idempotent():
    """Deferred combobox loading should only run once."""
    widget = StableDiffusionSettingsWidget.__new__(
        StableDiffusionSettingsWidget
    )
    widget._deferred_startup_loaded = False
    widget._load_versions_combobox = Mock()
    widget._load_pipelines_combobox = Mock()
    widget._load_models_combobox = Mock()
    widget._load_schedulers_combobox = Mock()
    widget._load_precision_combobox = Mock()
    widget.update_form = Mock()

    StableDiffusionSettingsWidget._finish_deferred_startup(widget)
    StableDiffusionSettingsWidget._finish_deferred_startup(widget)

    assert widget._deferred_startup_loaded is True
    widget._load_versions_combobox.assert_called_once_with()
    widget._load_pipelines_combobox.assert_called_once_with()
    widget._load_models_combobox.assert_called_once_with()
    widget._load_schedulers_combobox.assert_called_once_with()
    widget._load_precision_combobox.assert_called_once_with()
    widget.update_form.assert_called_once_with()


def test_show_event_finishes_deferred_startup_when_signal_was_missed():
    """First show should populate comboboxes even without the startup signal."""
    widget = StableDiffusionSettingsWidget.__new__(
        StableDiffusionSettingsWidget
    )
    widget._finish_deferred_startup = Mock()
    widget.update_form = Mock()
    event = Mock()

    with patch.object(BaseWidget, "showEvent", autospec=True):
        StableDiffusionSettingsWidget.showEvent(widget, event)

    widget._finish_deferred_startup.assert_called_once_with()
    widget.update_form.assert_called_once_with()