"""Tests for generator-form progress bar transitions."""

from types import MethodType, SimpleNamespace
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
    form._build_generate_request = Mock(return_value=None)
    form.start_progress_bar = Mock()
    form.set_progress_bar_value = Mock()
    form.generate = Mock()

    StableDiffusionGeneratorForm.handle_generate_button_clicked(form)

    assert form._waiting_for_backend_progress is True
    form.start_progress_bar.assert_called_once_with()
    form.set_progress_bar_value.assert_not_called()
    form.generate.assert_called_once_with(None)


def test_generate_click_uses_determinate_progress_for_loaded_model():
    """Repeat generations should skip the indeterminate spinner."""
    image_request = SimpleNamespace(model_path="/tmp/model.safetensors")
    form = StableDiffusionGeneratorForm.__new__(
        StableDiffusionGeneratorForm
    )
    form._waiting_for_backend_progress = False
    form._build_generate_request = Mock(return_value=image_request)
    form.start_progress_bar = Mock()
    form.set_progress_bar_value = Mock()
    form.generate = Mock()

    module.ModelResourceManager().set_model_state(
        image_request.model_path,
        module.ModelState.LOADED,
        "text_to_image",
    )

    StableDiffusionGeneratorForm.handle_generate_button_clicked(form)

    assert form._waiting_for_backend_progress is True
    form.set_progress_bar_value.assert_called_once_with(0)
    form.start_progress_bar.assert_not_called()
    form.generate.assert_called_once_with({"image_request": image_request})


def test_model_loaded_does_not_clear_spinner_while_waiting():
    """Loading completion should not clear the spinner before step updates."""
    form = StableDiffusionGeneratorForm.__new__(
        StableDiffusionGeneratorForm
    )
    form._busy_progress_models = set()
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


def test_rmbg_loading_starts_busy_progress_without_touching_sd_buttons():
    """RMBG activity should reuse the busy spinner without SD-only toggles."""
    form = StableDiffusionGeneratorForm.__new__(
        StableDiffusionGeneratorForm
    )
    form._generation_in_progress = False
    form._backend_progress_started = False
    form._waiting_for_backend_progress = False
    form.start_progress_bar = Mock()
    form.ui = SimpleNamespace(
        generate_button=Mock(),
        interrupt_button=Mock(),
    )

    StableDiffusionGeneratorForm.on_model_status_changed_signal(
        form,
        {"model": ModelType.RMBG, "status": ModelStatus.LOADING},
    )

    assert form._busy_progress_models == {ModelType.RMBG}
    form.start_progress_bar.assert_called_once_with()
    form.ui.generate_button.setEnabled.assert_not_called()
    form.ui.interrupt_button.setEnabled.assert_not_called()


def test_rmbg_ready_clears_busy_spinner_when_no_other_work_remains():
    """RMBG completion should return the progress bar to its idle state."""
    form = StableDiffusionGeneratorForm.__new__(
        StableDiffusionGeneratorForm
    )
    form._busy_progress_models = {ModelType.RMBG}
    form._waiting_for_backend_progress = False
    form._generation_in_progress = False
    form._set_progress_bar_idle = Mock()
    form.ui = SimpleNamespace(
        generate_button=Mock(),
        interrupt_button=Mock(),
    )

    StableDiffusionGeneratorForm.on_model_status_changed_signal(
        form,
        {"model": ModelType.RMBG, "status": ModelStatus.READY},
    )

    assert form._busy_progress_models == set()
    form._set_progress_bar_idle.assert_called_once_with()
    form.ui.generate_button.setEnabled.assert_not_called()
    form.ui.interrupt_button.setEnabled.assert_not_called()


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


def test_enable_image_to_image_mode_updates_enabled_state():
    """Image-to-image mode should become the only enabled input mode."""
    form = SimpleNamespace(
        ui=SimpleNamespace(
            image_to_image_settings=Mock(),
            inpaint_settings=Mock(),
        ),
        _set_image_mode_widgets=Mock(),
        _set_input_mode_state=Mock(),
    )

    StableDiffusionGeneratorForm._enable_image_to_image_mode(form)

    form._set_image_mode_widgets.assert_called_once_with(True, False)
    form._set_input_mode_state.assert_called_once_with(True, False)


def test_enable_inpaint_mode_updates_enabled_state():
    """Inpaint mode should disable img2img and enable outpaint settings."""
    form = SimpleNamespace(
        ui=SimpleNamespace(
            image_to_image_settings=Mock(),
            inpaint_settings=Mock(),
        ),
        _set_image_mode_widgets=Mock(),
        _set_input_mode_state=Mock(),
    )

    StableDiffusionGeneratorForm._enable_inpaint_mode(form)

    form._set_image_mode_widgets.assert_called_once_with(False, True)
    form._set_input_mode_state.assert_called_once_with(False, True)


def test_set_input_mode_state_emits_changes_after_updates():
    """Mode changes should update settings before notifying the canvas."""
    input_image_changed = Mock()
    form = SimpleNamespace(
        image_to_image_settings=SimpleNamespace(enabled=False),
        outpaint_settings=SimpleNamespace(enabled=True),
        update_image_to_image_settings=Mock(),
        update_outpaint_settings=Mock(),
        api=SimpleNamespace(
            art=SimpleNamespace(
                canvas=SimpleNamespace(input_image_changed=input_image_changed)
            )
        ),
    )

    def update_image_to_image_settings(**kwargs):
        form.image_to_image_settings.enabled = kwargs["enabled"]

    def update_outpaint_settings(**kwargs):
        form.outpaint_settings.enabled = kwargs["enabled"]

    form.update_image_to_image_settings.side_effect = (
        update_image_to_image_settings
    )
    form.update_outpaint_settings.side_effect = update_outpaint_settings
    form._update_input_mode_enabled = MethodType(
        StableDiffusionGeneratorForm._update_input_mode_enabled,
        form,
    )
    form._emit_input_mode_change = MethodType(
        StableDiffusionGeneratorForm._emit_input_mode_change,
        form,
    )

    StableDiffusionGeneratorForm._set_input_mode_state(
        form,
        image_to_image_enabled=True,
        inpaint_enabled=False,
    )

    form.update_image_to_image_settings.assert_called_once_with(enabled=True)
    form.update_outpaint_settings.assert_called_once_with(enabled=False)
    assert form.image_to_image_settings.enabled is True
    assert form.outpaint_settings.enabled is False
    input_image_changed.assert_any_call(
        "image_to_image_settings",
        "enabled",
        True,
    )
    input_image_changed.assert_any_call(
        "outpaint_settings",
        "enabled",
        False,
    )


def test_initialize_image_mode_restores_active_mode_without_signals():
    """Startup should normalize the visible mode from stored enabled flags."""
    form = SimpleNamespace(
        image_to_image_settings=SimpleNamespace(enabled=True),
        outpaint_settings=SimpleNamespace(enabled=False),
        ui=SimpleNamespace(
            image_mode_combobox=Mock(),
        ),
        _set_image_mode_widgets=Mock(),
        _set_input_mode_state=Mock(),
    )

    StableDiffusionGeneratorForm._initialize_image_mode(form)

    form._set_image_mode_widgets.assert_called_once_with(True, False)
    form._set_input_mode_state.assert_called_once_with(
        True,
        False,
        emit_signal=False,
    )
    form.ui.image_mode_combobox.setCurrentIndex.assert_called_once_with(1)