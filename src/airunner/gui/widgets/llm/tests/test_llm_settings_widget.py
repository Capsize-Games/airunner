"""
Test suite for llm_settings_widget.py in LLM widgets.
"""

import pytest
from airunner.gui.widgets.llm import llm_settings_widget
from unittest.mock import MagicMock, patch


@pytest.fixture
def settings_widget(qtbot):
    widget = llm_settings_widget.LLMSettingsWidget()
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_llm_settings_widget_constructs(settings_widget):
    assert settings_widget is not None


def test_initialize_form_runs(settings_widget):
    settings_widget.initialize_form()


def test_on_model_path_textChanged_updates_settings(
    settings_widget, monkeypatch
):
    called = {}
    monkeypatch.setattr(
        settings_widget,
        "update_llm_generator_settings",
        lambda k, v: called.update({k: v}),
    )
    settings_widget.on_model_path_textChanged("/tmp/model")
    assert called == {"model_path": "/tmp/model"}


def test_on_model_service_currentTextChanged_toggles_visibility(
    settings_widget, monkeypatch
):
    settings_widget.api = MagicMock()
    settings_widget.ui.remote_model_path = MagicMock()
    settings_widget.on_model_service_currentTextChanged("remote")
    settings_widget.ui.remote_model_path.show.assert_called()
    settings_widget.on_model_service_currentTextChanged("local")
    settings_widget.ui.remote_model_path.hide.assert_called()


def test_toggle_use_cache_updates_chatbot(settings_widget, monkeypatch):
    called = {}
    monkeypatch.setattr(
        settings_widget, "update_chatbot", lambda k, v: called.update({k: v})
    )
    settings_widget.toggle_use_cache(True)
    assert called == {"use_cache": True}


def test_toggle_model_path_visibility_shows_and_hides(settings_widget):
    settings_widget.ui.remote_model_path = MagicMock()
    settings_widget._toggle_model_path_visibility(True)
    settings_widget.ui.remote_model_path.show.assert_called()
    settings_widget._toggle_model_path_visibility(False)
    settings_widget.ui.remote_model_path.hide.assert_called()


def test_early_stopping_toggled_and_do_sample_toggled(
    settings_widget, monkeypatch
):
    called = {}
    monkeypatch.setattr(
        settings_widget, "update_chatbot", lambda k, v: called.update({k: v})
    )
    settings_widget.early_stopping_toggled(True)
    settings_widget.do_sample_toggled(False)
    assert called == {"early_stopping": True, "do_sample": False}


def test_toggle_leave_model_in_vram_updates_memory(
    settings_widget, monkeypatch
):
    called = {}
    monkeypatch.setattr(
        settings_widget,
        "update_memory_settings",
        lambda k, v: called.update({k: v}),
    )
    settings_widget.toggle_leave_model_in_vram(True)
    assert called == {
        "unload_unused_models": False,
        "move_unused_model_to_cpu": False,
    }


def test_on_llm_model_download_progress_shows_and_hides(settings_widget):
    settings_widget.ui.progressBar = MagicMock()
    settings_widget.on_llm_model_download_progress({"percent": 0})
    settings_widget.ui.progressBar.setVisible.assert_called_with(False)
    settings_widget.on_llm_model_download_progress({"percent": 50})
    settings_widget.ui.progressBar.setVisible.assert_called_with(True)
    settings_widget.ui.progressBar.setValue.assert_called_with(50)
    settings_widget.on_llm_model_download_progress({"percent": 100})
    settings_widget.ui.progressBar.setVisible.assert_called_with(False)
