"""Tests for generator-form progress bar transitions."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.art.gui.widgets.stablediffusion import (
    stablediffusion_generator_form as module,
)
from airunner.components.art.gui.widgets.stablediffusion.stablediffusion_generator_form import (  # noqa: E501
    StableDiffusionGeneratorForm,
)
from airunner.enums import ModelStatus, ModelType


def test_generate_click_keeps_spinner_pending_until_backend_progress():
    """Generate should enter the waiting state before backend steps arrive."""
    form = StableDiffusionGeneratorForm.__new__(
        StableDiffusionGeneratorForm
    )
    form._waiting_for_backend_progress = False
    form.start_progress_bar = Mock()
    form.generate = Mock()

    StableDiffusionGeneratorForm.handle_generate_button_clicked(form)

    assert form._waiting_for_backend_progress is True
    form.start_progress_bar.assert_called_once_with()
    form.generate.assert_called_once_with(None)


def test_model_loaded_does_not_clear_spinner_while_waiting():
    """Loading completion should not clear the spinner before step updates."""
    form = StableDiffusionGeneratorForm.__new__(
        StableDiffusionGeneratorForm
    )
    form._waiting_for_backend_progress = True
    form.stop_progress_bar = Mock()
    form.ui = SimpleNamespace(
        generate_button=Mock(),
        interrupt_button=Mock(),
    )

    StableDiffusionGeneratorForm.on_model_status_changed_signal(
        form,
        {"model": ModelType.SD, "status": ModelStatus.LOADED},
    )

    form.stop_progress_bar.assert_not_called()
    form.ui.generate_button.setEnabled.assert_called_once_with(True)
    form.ui.interrupt_button.setEnabled.assert_called_once_with(True)


def test_progress_signal_switches_bar_to_real_percentage(monkeypatch):
    """First backend progress should replace the busy animation."""
    progress_bar = Mock()
    progress_bar.maximum.return_value = 0
    form = StableDiffusionGeneratorForm.__new__(
        StableDiffusionGeneratorForm
    )
    form._waiting_for_backend_progress = True
    form.ui = SimpleNamespace(progress_bar=progress_bar)

    monkeypatch.setattr(module.QApplication, "processEvents", lambda: None)

    StableDiffusionGeneratorForm.handle_progress_bar(
        form,
        {"step": 2, "total": 10},
    )

    assert form._waiting_for_backend_progress is False
    progress_bar.setRange.assert_called_once_with(0, 100)
    progress_bar.setFormat.assert_called_with("Generating %p%")
    progress_bar.setValue.assert_called_once_with(20)


def test_zero_progress_keeps_spinner_pending():
    """Step zero should not switch the bar out of busy mode."""
    progress_bar = Mock()
    form = StableDiffusionGeneratorForm.__new__(
        StableDiffusionGeneratorForm
    )
    form._waiting_for_backend_progress = True
    form._backend_progress_started = False
    form.ui = SimpleNamespace(progress_bar=progress_bar)

    StableDiffusionGeneratorForm.handle_progress_bar(
        form,
        {"step": 0, "total": 10},
    )

    assert form._waiting_for_backend_progress is True
    assert form._backend_progress_started is False
    progress_bar.setRange.assert_not_called()
    progress_bar.setValue.assert_not_called()