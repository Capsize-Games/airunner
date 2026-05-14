"""Tests for unload handling in the model status widget."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.model_management.gui.model_status_widget import (
    ModelStatusWidget,
)
from airunner.enums import SignalCode


def test_resolve_unload_request_maps_rmbg_model():
    """RMBG rows should resolve to the dedicated unload signal."""
    request = ModelStatusWidget._resolve_unload_request(
        SimpleNamespace(
            model_id="briaai/RMBG-2.0",
            model_type="rmbg",
        )
    )

    assert request == (
        SignalCode.RMBG_UNLOAD_SIGNAL,
        {"model_id": "briaai/RMBG-2.0"},
    )


def test_resolve_unload_request_maps_text_to_image_to_sd_unload():
    """Text-to-image rows should reuse the SD unload path."""
    request = ModelStatusWidget._resolve_unload_request(
        SimpleNamespace(
            model_id="/models/art/zimage",
            model_type="text_to_image",
        )
    )

    assert request == (SignalCode.SD_UNLOAD_SIGNAL, {})


def test_unload_model_emits_resolved_signal():
    """Widget unload requests should flow through the shared mediator."""
    mediator = Mock()
    widget = SimpleNamespace(signal_mediator=mediator)
    model_info = SimpleNamespace(model_id="briaai/RMBG-2.0", model_type="rmbg")

    result = ModelStatusWidget._unload_model(widget, model_info)

    assert result is True
    mediator.emit_signal.assert_called_once_with(
        SignalCode.RMBG_UNLOAD_SIGNAL,
        {"model_id": "briaai/RMBG-2.0"},
    )


def test_unload_model_routes_llm_through_api_service(monkeypatch):
    """LLM widget unloads should use the LLM service boundary first."""
    mediator = Mock()
    widget = SimpleNamespace(signal_mediator=mediator)
    llm_service = SimpleNamespace(unload=Mock())

    monkeypatch.setattr(
        ModelStatusWidget,
        "_current_gui_api",
        staticmethod(lambda _widget=None: SimpleNamespace(llm=llm_service)),
    )

    result = ModelStatusWidget._unload_model(
        widget,
        SimpleNamespace(model_id="Qwen", model_type="llm"),
    )

    assert result is True
    llm_service.unload.assert_called_once_with({})
    mediator.emit_signal.assert_not_called()


def test_current_gui_api_prefers_enclosing_window_api(monkeypatch):
    """The status widget should prefer MainWindow-bound API over globals."""
    window = SimpleNamespace(api="window-api")
    widget = SimpleNamespace(
        api=None,
        parentWidget=lambda: None,
        window=lambda: window,
    )

    monkeypatch.setattr(
        "PySide6.QtWidgets.QApplication.instance",
        lambda: SimpleNamespace(api="app-api", main_window=None),
    )

    api = ModelStatusWidget._current_gui_api(widget)

    assert api == "window-api"


def test_unload_model_returns_false_for_unknown_type():
    """Unsupported rows should not emit unload signals."""
    mediator = Mock()
    widget = SimpleNamespace(signal_mediator=mediator)
    model_info = SimpleNamespace(model_id="custom", model_type="unknown")

    result = ModelStatusWidget._unload_model(widget, model_info)

    assert result is False
    mediator.emit_signal.assert_not_called()


def test_can_unload_model_requires_loaded_state():
    """Rows should only enable unload once the model is loaded."""
    model_info = SimpleNamespace(
        state=SimpleNamespace(value="loading"),
        can_unload=False,
    )

    assert ModelStatusWidget._can_unload_model(model_info) is False


def test_display_model_name_prefers_resolved_llm_name(monkeypatch):
    """LLM rows should prefer the configured human-readable model name."""
    monkeypatch.setattr(
        ModelStatusWidget,
        "_resolve_llm_display_name",
        staticmethod(lambda _model_id: "Qwen3.5-9B"),
    )

    name = ModelStatusWidget._display_model_name(
        SimpleNamespace(model_id="/models/llm/Qwen", model_type="llm")
    )

    assert name == "Qwen3.5-9B"