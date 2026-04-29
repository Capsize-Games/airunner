"""Focused tests for SettingsMixin API resolution behavior."""

from types import SimpleNamespace

from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)


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