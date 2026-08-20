"""Unit tests for the model resource status widget (the stats panel).

Covers the configured-model fallback that keeps the stats panel showing which
model is loaded even when daemon runtime summaries do not populate the shared
resource manager, plus the display-name resolution used for active-model rows.

These tests construct the widget via ``__new__`` so no QApplication or daemon
is required: only the pure resolution helpers are exercised.
"""

from __future__ import annotations

from types import SimpleNamespace

from airunner.components.model_management.gui.model_status_widget import (
    ModelStatusWidget,
)
from airunner.components.model_management.types import ModelState


class _Record:
    """Minimal attribute object mirroring ``ResourceRecord`` access."""

    def __init__(self, **values) -> None:
        self._values = values

    def __getattr__(self, name):
        try:
            return self._values[name]
        except KeyError:
            raise AttributeError(name) from None


def _widget(settings_factory) -> ModelStatusWidget:
    """Return a ModelStatusWidget without running the Qt constructor."""
    widget = ModelStatusWidget.__new__(ModelStatusWidget)
    widget._fallback_rows = []
    widget._fallback_computed_at = 0.0
    widget._settings_singleton = staticmethod(settings_factory)
    return widget


def test_fallback_rows_for_enabled_llm_only() -> None:
    """Only the enabled runtime appears, labeled as loaded."""
    app = _Record(
        llm_enabled=True,
        sd_enabled=False,
        tts_enabled=False,
        stt_enabled=False,
    )
    llm = _Record(
        model_path="/models/qwen3.5-9b-Q8_0.gguf",
        model_id="",
        model_version="",
    )

    def settings(name):
        return {"ApplicationSettings": app, "LLMGeneratorSettings": llm}.get(
            name
        )

    widget = _widget(settings)
    rows = widget._configured_model_fallback()

    assert len(rows) == 1
    row = rows[0]
    assert row.model_type == "llm"
    assert row.state is ModelState.LOADED
    assert row.model_id == "/models/qwen3.5-9b-Q8_0.gguf"
    assert row.can_unload is True


def test_fallback_empty_when_no_runtime_enabled() -> None:
    """An empty enabled set yields no fallback rows."""
    app = _Record(
        llm_enabled=False,
        sd_enabled=False,
        tts_enabled=False,
        stt_enabled=False,
    )
    widget = _widget(
        lambda name: app if name == "ApplicationSettings" else None
    )
    assert widget._configured_model_fallback() == []


def test_fallback_caches_rows() -> None:
    """Repeated refreshes reuse the cached rows without new settings reads."""
    app = _Record(
        llm_enabled=True,
        sd_enabled=False,
        tts_enabled=False,
        stt_enabled=False,
    )
    llm = _Record(model_id="qwen3.5-9b", model_path="", model_version="")

    calls = {"count": 0}

    def settings(name):
        calls["count"] += 1
        return {"ApplicationSettings": app, "LLMGeneratorSettings": llm}.get(
            name
        )

    widget = _widget(settings)
    first = widget._configured_model_fallback()
    second = widget._configured_model_fallback()

    assert first == second
    # First call reads ApplicationSettings + LLMGeneratorSettings; the cached
    # second call must not touch the settings backend again.
    assert calls["count"] == 2


def test_configured_llm_model_id_prefers_model_path() -> None:
    """The resolved LLM id follows path > id > version precedence."""
    llm = _Record(
        model_path="/models/qwen3.5-9b-Q8_0.gguf",
        model_id="qwen3.5-9b",
        model_version="v1",
    )
    widget = _widget(
        lambda name: llm if name == "LLMGeneratorSettings" else None
    )
    assert widget._configured_llm_model_id() == "/models/qwen3.5-9b-Q8_0.gguf"


def test_configured_llm_model_id_falls_back_to_label() -> None:
    """A missing LLM configuration still yields a stable label."""
    widget = _widget(lambda name: None)
    assert widget._configured_llm_model_id() == "LLM"


def test_display_model_name_llm_resolves_config_name(monkeypatch) -> None:
    """Active-model rows show the friendly LLM name from provider config."""
    store = SimpleNamespace(
        get_singleton=lambda name, create_if_missing=True: _Record(
            model_id="qwen3.5-9b",
            model_version="",
            model_path="",
        )
    )
    monkeypatch.setattr(
        "airunner.components.model_management.gui.model_status_widget."
        "get_resource_store",
        lambda: store,
    )
    info = SimpleNamespace(
        model_id="qwen3.5-9b",
        model_type="llm",
        state=ModelState.LOADED,
    )
    name = ModelStatusWidget._display_model_name(info)
    assert "Qwen3.5" in name


def test_display_model_name_falls_back_to_short_path(monkeypatch) -> None:
    """Unresolvable model ids degrade to the path basename."""
    store = SimpleNamespace(
        get_singleton=lambda name, create_if_missing=True: _Record()
    )
    monkeypatch.setattr(
        "airunner.components.model_management.gui.model_status_widget."
        "get_resource_store",
        lambda: store,
    )
    info = SimpleNamespace(
        model_id="some/custom/model/path.gguf",
        model_type="llm",
        state=ModelState.LOADED,
    )
    assert ModelStatusWidget._display_model_name(info) == "path.gguf"
