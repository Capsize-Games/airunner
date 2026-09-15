"""Round-trip tests for the QSettings-backed client-local settings layer."""

from PySide6.QtCore import QSettings

from airunner.utils.settings.client_settings import (
    current_tool,
    get_client_setting,
    is_dark,
    is_maximized,
    run_setup_wizard,
    set_client_setting,
    set_current_tool,
)


def _patch_settings(monkeypatch, tmp_path):
    """Point the client-settings layer at a throwaway INI file."""
    ini = str(tmp_path / "settings.ini")
    monkeypatch.setattr(
        "airunner.utils.settings.client_settings.get_qsettings",
        lambda: QSettings(ini, QSettings.Format.IniFormat),
    )
    return ini


def test_defaults_apply_when_unset(monkeypatch, tmp_path):
    _patch_settings(monkeypatch, tmp_path)
    assert is_dark() is True
    assert current_tool() == "brush"
    assert run_setup_wizard() is True
    assert is_maximized() is False


def test_round_trip_write_read(monkeypatch, tmp_path):
    _patch_settings(monkeypatch, tmp_path)
    set_current_tool("move")
    assert current_tool() == "move"
    set_client_setting("dark_mode_enabled", False)
    assert is_dark() is False
    set_client_setting("is_maximized", True)
    assert is_maximized() is True


def test_none_is_not_persisted(monkeypatch, tmp_path):
    _patch_settings(monkeypatch, tmp_path)
    set_current_tool("move")
    # A None write is skipped, so the last persisted value remains.
    set_client_setting("current_tool", None)
    assert current_tool() == "move"


def test_unknown_key_ignored(monkeypatch, tmp_path):
    _patch_settings(monkeypatch, tmp_path)
    set_client_setting("not_a_real_field", 123)
    assert get_client_setting("not_a_real_field", "fallback") == "fallback"
