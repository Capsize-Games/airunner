"""Focused tests for SettingsMixin API resolution behavior."""

from types import SimpleNamespace

from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.enums import SignalCode


class DummySettingsObject(SettingsMixin):
    """Minimal SettingsMixin carrier for API-resolution tests."""


def test_settings_mixin_uses_qt_application_api(monkeypatch):
    """Qt application API should be preferred over global API lookup."""
    expected_api = object()
    qt_app = SimpleNamespace(api=expected_api)

    monkeypatch.setattr(
        "PySide6.QtWidgets.QApplication.instance",
        lambda: qt_app,
    )
    monkeypatch.setattr(
        "PySide6.QtCore.QCoreApplication.instance",
        lambda: None,
    )

    settings = DummySettingsObject()

    assert settings.api is expected_api


def test_settings_mixin_peeks_global_api_without_creation(monkeypatch):
    """No-GUI paths must not create the GUI API singleton implicitly."""
    calls = []

    monkeypatch.setattr(
        "PySide6.QtWidgets.QApplication.instance",
        lambda: None,
    )
    monkeypatch.setattr(
        "PySide6.QtCore.QCoreApplication.instance",
        lambda: None,
    )

    def fake_get_api(*, create_if_missing=True):
        calls.append(create_if_missing)
        return None

    monkeypatch.setattr(
        "airunner.components.server.api.server.get_api",
        fake_get_api,
    )

    settings = DummySettingsObject()

    assert settings.api is None
    assert calls == [False]


def test_settings_mixin_falls_back_to_emit_signal():
    """Settings updates should still emit when api lacks helper methods."""
    emitted = []
    host = SimpleNamespace(
        api=SimpleNamespace(
            emit_signal=lambda code, data=None: emitted.append((code, data))
        )
    )

    SettingsMixin._notify_api_or_app(
        host,
        setting_name="llm_generator_settings",
        column_name="current_conversation_id",
        val=123,
    )

    assert emitted == [
        (
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL,
            {
                "setting_name": "llm_generator_settings",
                "column_name": "current_conversation_id",
                "val": 123,
            },
        )
    ]